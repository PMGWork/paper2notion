# Paper2Notion

## 概要
PDF論文ファイルをアップロードするだけで、AI（Gemini）によるメタデータ抽出・CrossrefによるDOI検索・Notion連携まで自動化するアプリです。

- PDFからGeminiでタイトル・著者・要旨などを自動抽出
- Crossref APIでタイトル検索し、類似度が高い場合のみDOIを自動取得
- DOIが採用された場合はCrossrefの正式メタデータで上書き
- 英語/日本語の自動判定＆英語論文のみアブストラクト自動翻訳
- Dropbox経由でPDFをアップロードし、Notionに論文情報を送信
- UI上で自動判定結果やDOI採用/不採用、タイトル類似度も確認可能

## 使い方

1. 必要なPythonパッケージをインストール
    ```
    pip install -r requirements.txt
    ```

2. `.env`にGemini APIキーなどを設定

3. Streamlitアプリを起動
    ```
    streamlit run main.py
    ```

4. ブラウザでアプリにアクセスし、PDFファイルをアップロード

5. 必要に応じてDropbox認証を行う

6. 「Notionに送信」ボタンを押すと、以下の流れで処理されます
    - GeminiでPDFからメタデータ抽出
    - Crossrefでタイトル検索し、タイトル類似度0.8以上の場合のみDOIを採用
    - DOIが採用された場合はCrossrefメタデータで上書き
    - 英語論文の場合はアブストラクトを日本語に自動翻訳
    - DropboxにPDFをアップロードし、Notionに論文情報を送信

## 注意点・仕様

- CrossrefでDOIが見つかっても、タイトル類似度が低い場合はDOIを採用しません
- DOIが採用されなかった場合はGemini抽出メタデータのみで処理します
- 英語/日本語の自動判定はlangdetectを利用
- .envやキャッシュファイルは.gitignoreで管理
- 詳細なログや判定結果はUI上に表示されます

## 開発・カスタマイズ

- タイトル類似度のしきい値や判定ロジックは`utils/metadata.py`・`main.py`で調整可能
- Notion連携やDropbox連携の詳細は`utils/notion.py`・`utils/dropbox.py`を参照

## ライセンス
MIT
