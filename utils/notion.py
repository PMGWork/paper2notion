import requests
from config import NOTION_API_KEY, NOTION_DATABASE_ID

def send_to_notion(meta, summary, pdf_url=None, pdf_name=None):
    """NotionにPaperページを作成"""
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        return False, "Notion APIキーまたはデータベースIDが設定されていません"

    # ブロック構造の準備
    children = []

    # PDFファイルのブロックがある場合
    if pdf_url:
        children.append({
            "object": "block",
            "type": "file",
            "file": {
                "caption": [{"type": "text", "text": {"content": f"Uploaded PDF: {pdf_name}"}}],
                "type": "external",
                "external": {
                    "url": pdf_url
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

    # PDFリンクがある場合
    if pdf_url:
        properties["PDF"] = {
            "files": [
                {
                    "type": "external",
                    "name": pdf_name or "PDF Link",
                    "external": {
                        "url": pdf_url
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