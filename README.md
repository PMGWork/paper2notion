# Paper2Notion

## 概要

`Paper2Notion` は、PDF形式の論文ファイルをアップロードするだけで、AIによるメタデータ抽出、Crossrefを利用したDOI検索、そしてNotionデータベースへの情報登録までを自動化するStreamlitアプリケーションです。

主な機能：

-   **メタデータ自動抽出**: アップロードされたPDFから、GoogleのGeminiモデルを利用して論文のタイトル、著者、抄録、発行年、ジャーナル名を抽出します。
-   **DOI自動検索と検証**: 抽出されたタイトルを基にCrossref APIを検索し、関連するDOIを特定します。タイトルの類似度があらかじめ設定された閾値（デフォルト0.8）以上の場合にのみ、そのDOIを採用します。
-   **Crossrefメタデータによる補完**: DOIが採用された場合、Crossrefから取得した正式なメタデータで既存情報を上書き・補完します。ただし、Crossrefの抄録が空の場合は、Geminiが抽出した抄録を維持します。
-   **多言語対応と自動翻訳**: 論文の言語（英語または日本語）を自動で判定します。英語の論文の場合、抄録を自動的に日本語へ翻訳します。
-   **全文要約**: Geminiモデルを利用し、論文全体の背景、目的、提案手法、結果、結論、議論を構造化して要約します。
-   **Notion連携**: 抽出・整形された全ての論文情報を、指定されたNotionデータベースへ自動で送信・登録します。
-   **進捗表示と結果確認**: UI上で、メタデータ抽出、DOI検索、翻訳、Notion送信などの処理状況や、DOIの採用/不採用、タイトルの類似度などをリアルタイムで確認できます。

## セットアップ

### 前提条件

-   Python 3.8以上
-   Gemini APIキー

### インストール

1.  **リポジトリをクローンします（まだの場合）：**
    ```bash
    git clone https://github.com/your-username/paper2notion-python.git
    cd paper2notion-python
    ```

2.  **必要なPythonパッケージをインストールします：**
    ```bash
    pip install -r requirements.txt
    ```

3.  **環境変数を設定します：**
    プロジェクトルートに `.env` ファイルを作成し、以下の情報を記述します。
    ```env
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    NOTION_API_KEY="YOUR_NOTION_API_KEY"
    NOTION_DATABASE_ID="YOUR_NOTION_DATABASE_ID"
    ```
    -   `GEMINI_API_KEY`: [Google AI Studio](https://aistudio.google.com/app/apikey) で取得したAPIキー。
    -   `NOTION_API_KEY`: NotionのインテグレーションAPIキー。
    -   `NOTION_DATABASE_ID`: 論文情報を保存するNotionデータベースのID。

    `.env` ファイルは `.gitignore` によってリポジトリには含まれません。

## 使い方

1.  **Streamlitアプリケーションを起動します：**
    ```bash
    streamlit run main.py
    ```

2.  **ブラウザでアプリにアクセスします：**
    ターミナルに表示されたURL（通常は `http://localhost:8501`）を開きます。

3.  **PDFファイルをアップロードします：**
    「論文PDF」セクションのファイルアップローダーを使って、解析したい論文のPDFファイルを選択します。

4.  **「Notionに送信」ボタンをクリックします：**
    クリック後、以下の処理が自動的に実行されます。
    1.  GeminiによるPDFからのメタデータ抽出。
    2.  抽出タイトルに基づくCrossrefでのDOI検索。
    3.  タイトル類似度が閾値（デフォルト0.8）以上の場合、DOIを採用。
    4.  DOIが採用された場合、Crossrefのメタデータで情報を更新・補完。
    5.  英語論文の場合、抄録を日本語に自動翻訳。
    6.  論文全体の構造化要約を作成。
    7.  全ての情報をNotionデータベースに送信。

## 設定とカスタマイズ

-   **タイトル類似度の閾値**: DOI採用の判断基準となるタイトルの類似度スコアの閾値は、`main.py`内の `is_similar` 関数の `threshold` 引数で調整可能です。
-   **Crossref検索ロジック**: `utils/metadata.py` 内の `search_doi_by_title` 関数や `get_metadata_from_doi` 関数で、Crossref APIとの連携方法を調整できます。
-   **Notion連携**: Notionへのデータ送信ロジックは `utils/notion.py` で定義されています。送信するプロパティやデータベースのマッピングなどを変更できます。
-   **プロンプト**: Geminiモデルへの指示（プロンプト）は `main.py` 内に記述されています。抽出項目や要約の形式などを変更したい場合は、これらのプロンプトを編集してください。

## 注意点と仕様

-   **DOIの採用基準**: CrossrefでDOIが見つかったとしても、抽出された論文タイトルとの類似度が設定された閾値に満たない場合は、そのDOIは採用されず、Geminiが抽出したメタデータが主として使用されます。
-   **言語判定**: 論文の言語（英語/日本語）の自動判定には `langdetect` ライブラリを使用しています。
-   **キャッシュファイル**: Streamlitやその他のライブラリが生成するキャッシュファイルは、`.gitignore` によってバージョン管理から除外されています。
-   **ログとフィードバック**: 処理の各ステップにおける詳細なログ、エラーメッセージ、判定結果（DOIの採用状況、類似度スコアなど）は、StreamlitアプリケーションのUI上に直接表示されます。

## 開発

### ディレクトリ構成

```
paper2notion-python/
├── .streamlit/
│   └── config.toml        # Streamlit設定ファイル (オプション)
├── utils/
│   ├── __init__.py
│   ├── gemini.py          # Gemini API連携モジュール
│   ├── metadata.py        # メタデータ処理、Crossref API連携モジュール
│   ├── models.py          # Pydanticモデル定義 (PaperMeta)
│   └── notion.py          # Notion API連携モジュール
├── .env.example           # 環境変数設定ファイルのテンプレート
├── .gitignore
├── main.py                # Streamlitアプリケーションのメインスクリプト
├── README.md
└── requirements.txt       # Python依存パッケージリスト
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は `LICENSE` ファイル（もしあれば）を参照してください。
