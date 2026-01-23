# backend/app/db.py
import os

from dotenv import load_dotenv
from supabase import Client, create_client

# .envファイルを読み込む
load_dotenv()

url: str = os.environ["SUPABASE_URL"]
key: str = os.environ["SUPABASE_PUBLISHABLE_KEY"]

if not url or not key:
    raise ValueError("Supabase URL or Key is missing in .env file")

# クライアントの作成（シングルトンとして扱う）
supabase: Client = create_client(url, key)
