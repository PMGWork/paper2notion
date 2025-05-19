import dropbox
import streamlit as st
import urllib.parse
import requests
import os
import json
from pathlib import Path
from config import (
    DROPBOX_APP_KEY,
    DROPBOX_APP_SECRET,
    DROPBOX_REDIRECT_URI,
    AUTH_URL,
    TOKEN_URL
)

# トークンを保存するファイルのパス
TOKEN_FILE_PATH = Path.home() / ".paper2notion" / "dropbox_token.json"

# アクセストークンを保存する関数
def save_access_token(access_token):
    try:
        # ディレクトリが存在しない場合は作成
        TOKEN_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        # トークンをJSONとして保存
        with open(TOKEN_FILE_PATH, 'w') as f:
            json.dump({"access_token": access_token}, f)
        return True
    except Exception as e:
        print(f"トークンの保存に失敗しました: {e}")
        return False

# アクセストークンを読み込む関数
def load_access_token():
    if not TOKEN_FILE_PATH.exists():
        return None

    try:
        with open(TOKEN_FILE_PATH, 'r') as f:
            data = json.load(f)
        return data.get("access_token")
    except Exception as e:
        print(f"トークンの読み込みに失敗しました: {e}")
        return None

# アクセストークンを削除する関数
def delete_access_token():
    if TOKEN_FILE_PATH.exists():
        try:
            TOKEN_FILE_PATH.unlink()
            return True
        except Exception as e:
            print(f"トークンの削除に失敗しました: {e}")
    return False

# Dropbox認証用URLを取得
def get_auth_url():
    params = {
        "client_id": DROPBOX_APP_KEY,
        "redirect_uri": DROPBOX_REDIRECT_URI,
        "response_type": "code",
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)

# アクセストークンを取得
def get_access_token(code):
    data = {
        "code": code,
        "client_id": DROPBOX_APP_KEY,
        "client_secret": DROPBOX_APP_SECRET,
        "redirect_uri": DROPBOX_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = requests.post(TOKEN_URL, data=data)
    if response.ok:
        return response.json()["access_token"]
    return None

# Dropboxにファイルをアップロードし、共有リンクを取得する関数
def upload_and_get_shared_link(file_bytes, file_name, dropbox_path, access_token):
    try:
        dbx = dropbox.Dropbox(access_token)
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
        return None