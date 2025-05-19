import os
from dotenv import load_dotenv

load_dotenv()

# Geminiの認証情報
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Notionの認証情報
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")

# Dropboxの認証情報
DROPBOX_APP_KEY = os.environ.get("DROPBOX_APP_KEY", "")
DROPBOX_APP_SECRET = os.environ.get("DROPBOX_APP_SECRET", "")
DROPBOX_REDIRECT_URI = os.environ.get("DROPBOX_REDIRECT_URI", "")

# Dropbox OAuth設定
AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"