import requests
from config import NOTION_API_KEY, NOTION_DATABASE_ID

def send_to_notion(meta, summary, pdf_bytes=None, pdf_name=None):
    # NotionにPaperページを作成（PDFを直接アップロード）
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        return False, "Notion APIキーまたはデータベースIDが設定されていません"

    # PDFファイルをアップロードしてfile_upload_idを取得
    file_upload_id = None
    if pdf_bytes:
        # 1. アップロードオブジェクト作成
        url_create = "https://api.notion.com/v1/file_uploads"
        headers_create = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        resp_create = requests.post(url_create, headers=headers_create, json={})
        if resp_create.status_code != 200:
            return False, f"Notionファイルアップロードオブジェクト作成失敗: {resp_create.status_code} - {resp_create.text}"
        upload_obj = resp_create.json()
        upload_url = upload_obj.get("upload_url")
        file_upload_id = upload_obj.get("id")
        if not upload_url or not file_upload_id:
            return False, "NotionファイルアップロードURLまたはID取得失敗"

        # 2. upload_urlにファイルPOST
        files = {"file": (pdf_name, pdf_bytes)}
        headers_upload = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": "2022-06-28"
            # Content-Typeはrequestsが自動でmultipart/form-dataを付与
        }
        resp_upload = requests.post(upload_url, headers=headers_upload, files=files)
        if resp_upload.status_code != 200:
            return False, f"Notionファイルアップロード失敗: {resp_upload.status_code} - {resp_upload.text}"

    # ブロック構造の準備
    children = []

    # PDFファイルのブロックがある場合
    if file_upload_id:
        children.append({
            "object": "block",
            "type": "file",
            "file": {
                "caption": [{"type": "text", "text": {"content": f"Uploaded PDF: {pdf_name}"}}],
                "type": "file_upload",
                "file_upload": {
                    "id": file_upload_id
                }
            }
        })

    # 要約のブロック追加
    if summary:
        current_paragraph_lines = []
        for line in summary.split('\n'):
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

    # プロパティの準備
    authors_list = [a.strip() for a in meta.get("authors", "").split(",") if a.strip()]
    journals_list = [j.strip() for j in meta.get("journals", "").split(",") if j.strip()]

    properties = {
        "タイトル": {
            "title": [{"text": {"content": meta.get("title", "No Title")}}]
        },
        "著者": {
            "multi_select": [{"name": a} for a in authors_list]
        },
        "発表年": {
            "number": meta.get("year") if isinstance(meta.get("year"), int) else None
        },
        "ジャーナル": {
            "multi_select": [{"name": j} for j in journals_list]
        },
        "DOI": {
            "url": meta.get("doi") if meta.get("doi") else None
        },
        "アブスト": {
            "rich_text": [{"text": {"content": meta.get("abstract", "")}}]
        }
    }

    # PDFファイルがある場合
    if file_upload_id:
        properties["PDF"] = {
            "files": [
                {
                    "type": "file_upload",
                    "name": pdf_name or "PDF",
                    "file_upload": {
                        "id": file_upload_id
                    }
                }
            ]
        }

    # APIリクエスト
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties,
        "children": children
    }

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return True, "Notionへの送信に成功しました"
    else:
        return False, f"Notion送信エラー: {response.status_code} - {response.text}"
