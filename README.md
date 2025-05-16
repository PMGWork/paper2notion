# Paper2Notion

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://paper2notion.streamlit.app/)

論文PDFを解析してメタデータを抽出し、Notionデータベースに保存するツールです。論文の内容を自動的に要約し、体系的に管理するのに役立ちます。

## 特徴

- DOIからメタデータを自動取得（タイトル、著者、ジャーナル、発表年など）
- PDFから不足情報をGemini AIで抽出
- 英語のアブストラクトを日本語に自動翻訳
- 論文の内容を「背景」「目的」「実装・実験方法」「結果」「結論」「議論」の項目で自動要約
- NotionデータベースにPDFへのリンク付きで整理して保存
- DropboxにPDFをアップロードしてNotion内でリンク可能

## 使い方

1. DOIを入力（任意）
2. 論文PDFをアップロード（必須）
3. 「Notionに送信」ボタンをクリック
4. 処理完了後、Notionデータベースに情報が保存されます

## セットアップ

### 必要なAPI

- **Gemini API**: PDFの解析と要約・翻訳に使用
- **Notion API**: データベースへの保存に使用
- **Dropbox API**: PDFの保存に使用（任意）

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/paper2notion.git
cd paper2notion

# 依存関係をインストール
pip install -r requirements.txt
```

### 環境変数の設定

プロジェクトディレクトリに `.env` ファイルを作成し、以下の内容を設定してください：

```
GEMINI_API_KEY=your_gemini_api_key
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id
DROPBOX_ACCESS_TOKEN=your_dropbox_access_token
```

### Notionデータベースの準備

以下のプロパティを持つデータベースを作成してください：

| プロパティ名 | タイプ | 説明 |
|------------|-------|------|
| タイトル | title | 論文のタイトル |
| 著者 | multi_select | 論文の著者（複数可） |
| 発表年 | number | 論文の発表年 |
| ジャーナル | multi_select | 掲載ジャーナル（複数可） |
| DOI | url | 論文のDOI URL |
| アブスト | rich_text | 論文のアブストラクト |
| PDF | files | アップロードしたPDFへのリンク |

## 実行方法

```bash
streamlit run main.py
```

ブラウザが開き、アプリケーションが表示されます。

## 論文の自動要約

Gemini AIを使用して以下の項目に分けて要約します：

- **背景**: 研究の背景や既存研究の課題
- **目的**: 研究の目的や解決しようとしている問題
- **実装・実験方法（提案）**: 提案手法や実験の詳細
- **結果**: 実験結果や評価
- **結論**: 研究から得られた結論
- **議論**: 結果の考察や今後の課題

## 技術スタック

- **Streamlit**: Web UIの構築
- **Google Gemini AI**: PDF解析と要約・翻訳
- **Notion API**: データベース連携
- **Dropbox API**: PDFファイル保存

## ライセンス

MIT

## 謝辞

本アプリはGemini API、Notion API、Dropbox APIを使用しています。
