import streamlit as st
import requests
import os
import json
import tempfile
import pathlib
from google import genai
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv
import dropbox
from io import BytesIO
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")
DROPBOX_ACCESS_TOKEN = os.environ.get("DROPBOX_ACCESS_TOKEN", "")

# スキーマ定義
class PaperMeta(BaseModel):
    title: str = ""
    authors: str = ""
    journals: str = ""
    year: int = 0
    abstract: str = ""

# DOIからメタ情報を取得する関数
def get_metadata_from_doi(doi):
    # arXiv IDの場合
    if doi.lower().startswith("arxiv:"):
        arxiv_id = doi.split(":")[1]
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        resp = requests.get(url)
        if resp.status_code != 200:
            return None
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        entry = root.find("{http://www.w3.org/2005/Atom}entry")
        if entry is None:
            return None
        title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip()
        authors = [author.find("{http://www.w3.org/2005/Atom}name").text for author in entry.findall("{http://www.w3.org/2005/Atom}author")]
        summary = entry.find("{http://www.w3.org/2005/Atom}summary").text.strip()
        published = entry.find("{http://www.w3.org/2005/Atom}published").text
        year = int(published[:4])
        arxiv_url = entry.find("{http://www.w3.org/2005/Atom}id").text
        return {
            "title": title,
            "authors": ", ".join(authors),
            "journals": "arXiv",
            "year": year,
            "doi": arxiv_url,
            "abstract": summary
        }

    # 通常のDOI
    url = f"https://api.crossref.org/works/{doi}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None
    data = resp.json()["message"]
    return {
        "title": data.get("title", [""])[0],
        "authors": ", ".join([f'{a.get("given", "")} {a.get("family", "")}' for a in data.get("author", [])]),
        "journals": data.get("container-title", [""])[0],
        "year": data.get("published-print", data.get("published-online", {})).get("date-parts", [[None]])[0][0],
        "doi": data.get("DOI", ""),
        "abstract": data.get("abstract", ""),
    }

# DropboxにPDFをアップロードし、共有リンクを取得する関数
def upload_to_dropbox_and_get_shared_link(file_bytes, file_name, dropbox_path):
    if not DROPBOX_ACCESS_TOKEN:
        st.warning("Dropboxアクセストークンが設定されていません。")
        return None
    try:
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        # Dropbox上のフルパス
        full_dropbox_path = f"/{dropbox_path.strip('/')}/{file_name}"

        # ファイルをアップロード (上書きモード)
        dbx.files_upload(file_bytes, full_dropbox_path, mode=dropbox.files.WriteMode("overwrite"))

        # 共有リンクを作成または取得
        try:
            # 既存のリンクを探す
            links = dbx.sharing_list_shared_links(path=full_dropbox_path, direct_only=True).links
            if links:
                shared_link_url = links[0].url
            else: # 既存のリンクがなければ新規作成
                link_metadata = dbx.sharing_create_shared_link_with_settings(full_dropbox_path)
                shared_link_url = link_metadata.url
        except dropbox.exceptions.ApiError as e:
            # 共有リンクが既に存在する場合のエラーをキャッチして既存のリンクを取得
            if e.error.is_shared_link_already_exists():
                links = dbx.sharing_list_shared_links(path=full_dropbox_path).links
                if links:
                    shared_link_url = links[0].url
                else:
                    raise Exception("共有リンクの取得に失敗しました。")
            else:
                raise

        # URLの末尾が ?dl=0 の場合、?raw=1 に変更すると直接表示/ダウンロードしやすくなる
        shared_link_url = shared_link_url.replace("?dl=0", "?raw=1")
        return shared_link_url
    except Exception as e:
        st.error(f"Dropbox処理エラー: {e}")
        return None

# Geminiにプロンプトを送信する関数
def send_prompt(pdf_path, prompt, schema: type = None):
    client = genai.Client(api_key=GEMINI_API_KEY)
    use_model = "gemini-2.5-flash-preview-04-17"
    if pdf_path.exists():
        kwargs = dict(
            model=use_model,
            contents=[
                types.Part.from_bytes(
                    data=pdf_path.read_bytes(),
                    mime_type='application/pdf',
                ),
                prompt
            ]
        )
    else:
        kwargs = dict(
            model=use_model,
            contents=[prompt]
        )
    if schema:
        kwargs["config"] = {
            "response_mime_type": "application/json",
            "response_schema": schema,
        }
    response = client.models.generate_content(**kwargs)
    if schema and hasattr(response, "parsed"):
        return response.parsed
    return response.text

# メイン処理
st.title("Paper2Notion")
st.write("DOI（任意）とPDF（必須）を入力してください。DOIから取得できなかった項目はPDFから取得します。")

if "meta" not in st.session_state:
    st.session_state.meta = None

doi_input = st.text_input("DOI（任意）")
pdf_file = st.file_uploader("論文PDF（必須）", type=["pdf"], key="pdf2")

if st.button("Notionに送信"):
    meta = {}
    # 1. DOIからメタデータ取得
    if doi_input:
        try:
            meta = get_metadata_from_doi(doi_input) or {}
            st.success("DOIからメタデータを取得しました")
            st.write(meta)
        except Exception as e:
            st.error(f"DOI取得エラー: {e}")

    # 2. PDFアップロード必須
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
        st.info(f"PDFファイル名: {st.session_state.uploaded_pdf_info['name']}")

        # 3. 不足メタデータをGeminiで構造体(JSON)で一括抽出
        missing_fields = []
        for field in ["title", "authors", "journals", "year", "abstract"]:
            if not meta.get(field):
                missing_fields.append(field)
        if missing_fields:
            prompt = (
                "この論文PDFから以下の情報を取得し、JSON形式で出力してください。\n"
                "'title', 'authors', 'journals', 'year', 'abstract'"
            )
            with st.spinner("PDFからメタ情報を取得中..."):
                try:
                    value = send_prompt(tmp_path, prompt, schema=PaperMeta)
                    st.success("PDFからメタデータを取得しました")
                    # PaperMetaインスタンスならdict化
                    if isinstance(value, PaperMeta):
                        value_dict = value.dict()
                    else:
                        value_dict = json.loads(value)
                    # missing_fieldsにある項目だけ更新
                    for key in missing_fields:
                        if key in value_dict:
                            meta[key] = value_dict[key]
                    st.write({k: value_dict[k] for k in missing_fields if k in value_dict})
                except Exception as e:
                    st.error(f"PDF取得エラー: {e}")

        # 4. アブスト翻訳
        if meta.get("abstract"):
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

        # 5. 全文要約
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

        # 6. Notionに送信
        if meta and summary:
            notion_meta = st.session_state.get("meta", {})
            notion_summary = st.session_state.get("pdf_summary", "")
            uploaded_pdf_info = st.session_state.get("uploaded_pdf_info")
            children = []

            # DropboxにPDFをアップロードし、ファイルブロックを追加
            if uploaded_pdf_info and DROPBOX_ACCESS_TOKEN:
                pdf_bytes = uploaded_pdf_info["bytes"]
                pdf_name = uploaded_pdf_info["name"]
                dropbox_folder = "Paper2Notion_Uploads"

                with st.spinner(f"'{pdf_name}' をDropboxにアップロード中..."):
                    pdf_public_url = upload_to_dropbox_and_get_shared_link(pdf_bytes, pdf_name, dropbox_folder)
                    st.session_state.pdf_public_url = pdf_public_url

                if pdf_public_url:
                    st.success(f"Dropboxへのアップロードが完了しました")
                    st.info(f"URL: {pdf_public_url}")
                    children.append({
                        "object": "block",
                        "type": "file",
                        "file": {
                            "caption": [{"type": "text", "text": {"content": f"Uploaded PDF: {pdf_name}"}}],
                            "type": "external",
                            "external": {
                                "url": pdf_public_url
                            }
                        }
                    })
                else:
                    st.warning("DropboxへのPDFアップロードに失敗したため、Notionにファイルリンクを追加できませんでした。")
            elif uploaded_pdf_info and not DROPBOX_ACCESS_TOKEN:
                 st.warning("Dropboxアクセストークンが未設定のため、PDFをアップロードできません。")

            if notion_summary:
                current_paragraph_lines = []
                for line in notion_summary.split('\n'):
                    stripped_line = line.strip()
                    if stripped_line.startswith("### "):
                        if current_paragraph_lines:
                            paragraph_text = "\n".join(current_paragraph_lines).strip()
                            if paragraph_text:
                                children.append({
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [{"type": "text", "text": {"content": paragraph_text}}]
                                    }
                                })
                            current_paragraph_lines = []
                        heading_content = stripped_line.replace("### ", "").strip()
                        if heading_content:
                            children.append({
                                "object": "block",
                                "type": "heading_3",
                                "heading_3": {
                                    "rich_text": [{"type": "text", "text": {"content": heading_content}}]
                                }
                            })
                    elif stripped_line or current_paragraph_lines:
                        current_paragraph_lines.append(line)
                if current_paragraph_lines:
                    paragraph_text = "\n".join(current_paragraph_lines).strip()
                    if paragraph_text:
                        children.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": paragraph_text}}]
                            }
                        })

            authors_list = [a.strip() for a in notion_meta.get("authors", "").split(",") if a.strip()]
            journals_list = [j.strip() for j in notion_meta.get("journals", "").split(",") if j.strip()]
            doi_url = notion_meta.get("doi", "")
            pdf_public_url_for_notion = st.session_state.get("pdf_public_url", None)
            pdf_name_for_notion = st.session_state.get("uploaded_pdf_info", {}).get("name", "PDF Link")

            properties = {
                "タイトル": {
                    "title": [{"text": {"content": notion_meta.get("title", "No Title")}}]
                },
                "著者": {
                    "multi_select": [{"name": a} for a in authors_list]
                },
                "発表年": {
                    "number": notion_meta.get("year") if isinstance(notion_meta.get("year"), int) else None
                },
                "ジャーナル": {
                    "multi_select": [{"name": j} for j in journals_list]
                },
                "DOI": {
                    "url": doi_url if doi_url else None
                },
                "アブスト": {
                    "rich_text": [{"text": {"content": notion_meta.get("abstract", "")}}]
                },
                "PDF": {
                    "files": [
                        {
                            "type": "external",
                            "name": pdf_name_for_notion,
                            "external": {
                                "url": pdf_public_url_for_notion
                            }
                        }
                    ] if pdf_public_url_for_notion else []
                }
            }
            data = {
                "parent": {"database_id": NOTION_DATABASE_ID},
                "properties": properties,
                "children": children
            }
            if NOTION_API_KEY and NOTION_DATABASE_ID:
                with st.spinner("Notionに送信中..."):
                    url = "https://api.notion.com/v1/pages"
                    headers = {
                        "Authorization": f"Bearer {NOTION_API_KEY}",
                        "Notion-Version": "2022-06-28",
                        "Content-Type": "application/json"
                    }
                    resp = requests.post(url, headers=headers, json=data)
                    if resp.status_code == 200:
                        st.success("Notionへの送信に成功しました")
                    else:
                        st.error(f"Notion送信エラー: {resp.status_code} - {resp.text}")
            else:
                st.warning("Notion APIキーまたはデータベースIDが設定されていません（環境変数 NOTION_API_KEY, NOTION_DATABASE_ID）")
    else:
        st.warning("PDFファイルをアップロードしてください。またはGemini APIキーが未設定です。")
