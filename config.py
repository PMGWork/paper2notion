import os
from dotenv import load_dotenv

load_dotenv()

# Geminiの認証情報
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Notionの認証情報
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")