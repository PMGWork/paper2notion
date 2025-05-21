import streamlit as st
import tempfile
import pathlib
import json
from io import BytesIO
import xml.etree.ElementTree as ET
from langdetect import detect, LangDetectException

# 自作モジュールのインポート
from config import GEMINI_API_KEY
from utils.models import PaperMeta
from utils.metadata import get_metadata_from_doi, search_doi_by_title, is_similar
from utils.gemini import send_prompt
from utils.notion import send_to_notion

# アプリケーションのメイン部分
st.title("Paper2Notion")
st.write("PDFファイルをアップロードしてください。")

# セッション状態の初期化
if "meta" not in st.session_state:
    st.session_state.meta = None

# ユーザー入力部分
pdf_file = st.file_uploader("論文PDF", type=["pdf"], key="pdf")

if st.button("Notionに送信"):
    meta = {}

    if pdf_file is not None and GEMINI_API_KEY:
        # PDFファイル情報をsession_stateに保存
        st.session_state.uploaded_pdf_info = {
            "name": pdf_file.name,
            "bytes": pdf_file.getvalue()
        }

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(st.session_state.uploaded_pdf_info["bytes"])
            tmp_path = pathlib.Path(tmp.name)

        st.success("PDFのアップロードが完了しました")

        # Geminiでメタデータを一括抽出
        prompt = (
            "この論文PDFから以下の情報を取得し、JSON形式で出力してください。\n"
            "'title', 'authors', 'journals', 'year', 'abstract'"
        )
        with st.spinner("PDFからメタ情報を取得中..."):
            try:
                value = send_prompt(tmp_path, prompt, schema=PaperMeta)
                st.success("PDFからメタデータを取得しました")
                # 結果の処理
                if isinstance(value, PaperMeta):
                    value_dict = value.dict()
                elif isinstance(value, str):
                    value_dict = json.loads(value)
                else:
                    value_dict = value

                meta.update(value_dict)
                st.write(meta)
            except Exception as e:
                st.error(f"PDF取得エラー: {e}")

        # タイトルでDOI検索 → 類似度判定 → Crossrefメタデータで上書き
        if meta.get("title"):
            with st.spinner("CrossrefでDOI検索中..."):
                doi = search_doi_by_title(meta["title"])
                if doi:
                    meta_crossref = get_metadata_from_doi(doi)
                    crossref_title = meta_crossref.get("title") if meta_crossref else ""
                    sim = is_similar(meta["title"], crossref_title, threshold=0.8)
                    st.info(f"CrossrefでDOIを取得: {doi}")
                    if sim and meta_crossref:
                        # Crossrefのabstractが空ならGemini抽出値を維持
                        if not meta_crossref.get("abstract") and meta.get("abstract"):
                            meta_crossref["abstract"] = meta["abstract"]
                        meta.update(meta_crossref)
                        st.success("Crossrefからメタデータを取得し上書きしました")
                        st.write(meta)
                    else:
                        st.warning("タイトル類似度が低いためDOIを採用しませんでした")
                else:
                    st.warning("CrossrefでDOIが見つかりませんでした")

        # 言語自動判定
        detected_lang = None
        if meta.get("abstract"):
            try:
                lang_code = detect(meta["abstract"])
                detected_lang = "日本語" if lang_code == "ja" else "英語"
            except LangDetectException:
                detected_lang = "不明"
        elif meta.get("title"):
            try:
                lang_code = detect(meta["title"])
                detected_lang = "日本語" if lang_code == "ja" else "英語"
            except LangDetectException:
                detected_lang = "不明"
        else:
            detected_lang = "不明"

        # アブスト翻訳（英語論文のみ自動判定で）
        if meta.get("abstract") and detected_lang == "英語":
            prompt = (
                "次のアブストラクトが日本語以外で記述されている場合は、日本語に翻訳してください。\n"
                "日本語で記述されている場合は、変更を加えずにそのまま出力してください。\n"
                "アブストの文章のみを出力してください。\n"
            )
            with st.spinner("アブストを翻訳中..."):
                try:
                    translated_abstract = send_prompt(tmp_path, prompt + meta["abstract"])
                    meta["abstract"] = translated_abstract
                    st.success("アブストの翻訳が完了しました")
                    st.code(translated_abstract, language="text", wrap_lines=True)
                except Exception as e:
                    st.warning(f"アブスト翻訳エラー: {e}")

        # 全文要約
        with st.spinner("論文内容を要約中..."):
            prompt = (
                "#与えられた論文のPDF資料をもとに、以下の内容のみを出力してください。\n"
                "### 背景\n"
                "背景の要約文を入力する\n"
                "### 目的\n"
                "目的の要約文を入力する\n"
                "### 実装・実験方法（提案）\n"
                "実装・実験方法（提案）の要約文を入力する\n"
                "### 結果\n"
                "結果の要約文を入力する\n"
                "### 結論\n"
                "結論の要約文を入力する\n"
                "### 議論\n"
                "議論の要約文を入力する\n"
            )
            try:
                summary = send_prompt(tmp_path, prompt)
                st.session_state.pdf_summary = summary
                st.success("論文内容の要約が完了しました")
                st.code(summary, language="markdown", wrap_lines=True)
            except Exception as e:
                st.warning(f"要約エラー: {e}")
                summary = ""

        st.session_state.meta = meta

        # Notionに送信
        if meta:
            summary = st.session_state.get("pdf_summary", "")
            pdf_bytes = st.session_state.uploaded_pdf_info["bytes"]
            pdf_name = st.session_state.uploaded_pdf_info["name"]

            with st.spinner("Notionに送信中..."):
                success, message = send_to_notion(meta, summary, pdf_bytes, pdf_name)
                if success:
                    st.success(message)
                else:
                    st.error(message)
    else:
        st.warning("PDFファイルをアップロードしてください。またはGemini APIキーが未設定です。")
