import os
import json
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")
DATA_FILE = "items.json"

def load_items():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_items(items):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

def ask_gemini(question, items):
    context = "\n".join([f"• {i['name']} → {i['location']}" for i in items]) if items else "Список пуст."
    prompt = f"Список вещей в гараже:\n{context}\n\nВопрос: {question}"
    
    # Используем самую простую и стабильную модель
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_KEY}"
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Ошибка: {str(e)}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    items = load_items()
    
    # Простая логика добавления (если есть запятая или слово "лежит")
    if "," in text or "лежит" in text or "положил" in text:
        items.append({"name": text.split()[0], "location": "неизвестно"}) # Упрощено для чистоты
        save_items(items)
        await update.message.reply_text("✅ Записал!")
    else:
        reply = ask_gemini(text, items)
        await update.message.reply_text(reply)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
