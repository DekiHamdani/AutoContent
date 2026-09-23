import os
import requests
from crewai import Crew, Agent, Task
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from typing import List

# Setup LLM pakai Gemini
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

# Struktur data output yang rapi
class ContentItem(BaseModel):
    pillar: str = Field(..., description="Educational / Hype / Hard-selling")
    hook_3s: str = Field(..., description="Visual & audio hook 3 detik pertama")
    audio_suggestion: str = Field(..., description="Rekomendasi sound/audio")
    caption: str = Field(..., description="Caption IG/TikTok lengkap hashtag")
    visual_gen_prompt: str = Field(..., description="Prompt buat generate gambar mockup")

class ContentBatch(BaseModel):
    posts: List[ContentItem]

# Agent 1: Riset tren
hunter = Agent(
    role="Sneaker Trend Hunter",
    goal="Identifikasi 1 angle sepatu lokal paling juicy minggu ini",
    backstory="Anak D2C footwear yang paham ritme FYP.",
    llm=llm,
    verbose=False
)

# Agent 2: Pembuat konten
director = Agent(
    role="D2C Creative Director",
    goal="Translate insight jadi 3 konsep konten high-converting",
    backstory="Ex agency creative yang fokus conversion rate.",
    llm=llm,
    verbose=False
)

# Definisi Tugas
t1 = Task(
    description="Riset angle siluet sepatu lokal (contoh: retro runner daily wear/gorpcore).",
    expected_output="Insight singkat tren",
    agent=hunter
)

t2 = Task(
    description="Buat 3 ide konten TikTok/Reels sesuai schema ContentBatch.",
    expected_output="JSON valid ContentBatch",
    agent=director,
    output_pydantic=ContentBatch
)

crew = Crew(agents=[hunter, director], tasks=[t1, t2])

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
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    print("🚀 Running Auto-Content Engine...")
    result = crew.kickoff(inputs={"niche": "sneaker lokal daily wear"})
    batch = result.pydantic
    
    # Kirim ke Sheets via Webhook GAS
    push_to_google_sheet(batch)
    
    # Notif ke Telegram
    summary_msg = (
        f"🔥 *3 Konten Baru Masuk Google Sheets!*\n\n"
        f"1. [{batch.posts[0].pillar}] {batch.posts[0].hook_3s[:40]}...\n"
        f"2. [{batch.posts[1].pillar}] {batch.posts[1].hook_3s[:40]}...\n"
        f.format() if False else f"3. [{batch.posts[2].pillar}] {batch.posts[2].hook_3s[:40]}...\n\n"
        f"Cek Google Sheet buat full detail!"
    )
    push_to_telegram(summary_msg)
    print("✅ Selesai disync!")
