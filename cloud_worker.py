import os
import json
import time
import requests
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Any

# Setup Google GenAI Client (mengambil GEMINI_API_KEY dari environment)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class ContentItem(BaseModel):
    pillar: str = Field(..., description="Educational / Hype / Hard-selling")
    hook_3s: str = Field(..., description="Visual & audio hook 3 detik pertama")
    audio_suggestion: str = Field(..., description="Rekomendasi sound/audio")
    caption: str = Field(..., description="Caption IG/TikTok lengkap hashtag")
    visual_gen_prompt: str = Field(..., description="Prompt buat generate gambar mockup")

class ContentBatch(BaseModel):
    posts: List[ContentItem]

def get_safe_hook(posts: List[Any], index: int, max_len: int = 30) -> str:
    try:
        if not posts or len(posts) <= index:
            return "-"
        item = posts[index]
        if isinstance(item, dict):
            val = item.get("hook_3s")
        else:
            val = getattr(item, "hook_3s", None)
        return str(val)[:max_len] if val else "-"
    except Exception:
        return "-"

def generate_content_with_gemini(niche: str) -> ContentBatch:
    prompt = f"""
    Kamu adalah D2C Footwear Creative Director dan Trend Hunter handal anak scene lokal/Jaksel.
    Riset 1 siluet/angle sepatu lokal paling juicy minggu ini ({niche}), 
    lalu buatkan 3 ide konten TikTok/Reels high-converting.
    """
    
    attempt = 1
    wait_time = 5  # Mulai dari jeda 5 detik
    
    while True:
        try:
            print(f"🔄 Mencoba generate konten ke-{attempt}...")
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ContentBatch,
                    temperature=0.7,
                ),
            )
            data = json.loads(response.text)
            print("✨ Berhasil generate konten dari Gemini!")
            return ContentBatch(**data)
        except Exception as e:
            print(f"⚠️ Gagal attempt {attempt} (Error: {e})")
            print(f"⏳ Menunggu {wait_time} detik sebelum coba lagi...")
            time.sleep(wait_time)
            attempt += 1
            # Naikkan jeda perlahan maksimal sampai 30 detik biar aman
            wait_time = min(wait_time + 5, 30)

def push_to_google_sheet(batch: ContentBatch):
    webhook_url = os.getenv("GAS_WEBHOOK_URL")
    if not webhook_url:
        print("⚠️ GAS_WEBHOOK_URL belum diset!")
        return
    payload = {"posts": [item.model_dump() for item in batch.posts]}
    response = requests.post(webhook_url, json=payload)
    print("Google Sheets Sync Response:", response.text)

def push_to_telegram(text: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("⚠️ Telegram token/chat_id belum diset.")
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    print("Telegram Sync Response:", response.text)

if __name__ == "__main__":
    print("🚀 Running Pure Gemini Auto-Content Engine (Infinite Retry)...")
    batch = generate_content_with_gemini("sneaker lokal daily wear / retro runner / gorpcore")
    
    # 1. Kirim ke Google Sheets via Webhook GAS
    push_to_google_sheet(batch)
    
    # 2. Notif ringkas ke Telegram (Aman pakai helper)
    p1 = get_safe_hook(batch.posts, 0, 30)
    p2 = get_safe_hook(batch.posts, 1, 30)
    p3 = get_safe_hook(batch.posts, 2, 30)
    
    summary_msg = (
        f"🔥 *3 Konten Baru Masuk Google Sheets!*\n\n"
        f"1. {p1}...\n"
        f"2. {p2}...\n"
        f"3. {p3}...\n\n"
        f"Cek Google Sheet buat full detail!"
    )
    push_to_telegram(summary_msg)
    print("✅ Selesai disync ke Telegram & Sheets!")
