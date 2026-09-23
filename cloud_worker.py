import os
import json
import requests
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List

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

def generate_content_with_gemini(niche: str) -> ContentBatch:
    prompt = f"""
    Kamu adalah D2C Footwear Creative Director dan Trend Hunter handal anak scene lokal/Jaksel.
    Riset 1 siluet/angle sepatu lokal paling juicy minggu ini ({niche}), 
    lalu buatkan 3 ide konten TikTok/Reels high-converting.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ContentBatch,
            temperature=0.7,
        ),
    )
    # Parse json string ke Pydantic model
    data = json.loads(response.text)
    return ContentBatch(**data)

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
    print("🚀 Running Pure Gemini Auto-Content Engine...")
    batch = generate_content_with_gemini("sneaker lokal daily wear / retro runner / gorpcore")
    
    # 1. Kirim ke Google Sheets via Webhook GAS
    push_to_google_sheet(batch)
    
    # 2. Notif ringkas ke Telegram
    p1 = batch.posts[0].hook_3s[:30] if len(batch.posts) > 0 else "-"
    p2 = batch.posts.hook_3s[:30] if len(batch.posts) > 1 else "-"
    p3 = batch.posts.hook_3s[:30] if len(batch.posts) > 2 else "-"
    
    summary_msg = (
        f"🔥 *3 Konten Baru Masuk Google Sheets!*\n\n"
        f"1. {p1}...\n"
        f"2. {p2}...\n"
        f"3. {p3}...\n\n"
        f"Cek Google Sheet buat full detail!"
    )
    push_to_telegram(summary_msg)
    print("✅ Selesai disync ke Telegram & Sheets!")
    
