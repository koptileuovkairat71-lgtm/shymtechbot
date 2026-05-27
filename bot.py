import os
import json
import requests
import asyncio
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

def parse_add(text):
    import re
    t = text.lower().strip()
    patterns = [
        r"(.+)\s+(?:положил|положила|лежит|находится|стоит|висит|храню)\s+(?::в|на|под|за|около|у|рядом)\s+(.+)",
        r"(?:положил|положила|убрал|кинул)\s+(.+)\s+(?::в|на|под|за)\s+(.+)",
    ]
    for p in patterns:
        m = re.match(p, t)
        if m and m.group(2):
            return m.group(1).strip().capitalize(), m.group(2).strip().capitalize()
    parts = t.split(",")
    if len(parts) >= 2:
        return parts[0].strip().capitalize(), parts[1].strip().capitalize()
    return None, None

def ask_gemini(question, items):
    if items:
        context = "Список вещей в гараже:\n" + "\n".join([f"• {i['name']} → {i['location']}" for i in items])
    else:
        context = "Список вещей пустой."
    
    prompt = f"{context}\n\nОтвечай коротко на русском. Вопрос: {question}"
    
    # ИСПОЛЬЗУЕМ gemini-1.5-pro ДЛЯ БОЛЬШЕЙ СТАБИЛЬНОСТИ
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_KEY}"
    
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = r.json()
        
        # Проверка ответа
        if "candidates" in data and len(data["candidates"]) > 0:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return f"Ошибка ИИ: Ответ не содержит текста. Данные: {data}"
            
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        return f"Ошибка ИИ: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я помогу найти вещи в гараже.\n\n"
        "➕ Добавить: «Ключ положил в шкаф»\n"
        "🔍 Найти: «Где ключи?»\n"
        "📋 Список: /list"
    )

async def list_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = load_items()
    if not items:
        await update.message.reply_text("📋 Список пустой!")
    else:
        msg = "📋 Все вещи:\n\n" + "\n".join([f"• {i['name']} → {i['location']}" for i in items])
        await update.message.reply_text(msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    items = load_items()
    name, location = parse_add(text)
    
    if name and location:
        items.append({"name": name, "location": location})
        save_items(items)
        await update.message.reply_text(f"✅ Сохранено!\n{name}: {location}")
        return
    
    reply = ask_gemini(text, items)
    await update.message.reply_text(reply)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_items))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен!")
    app.run_polling(drop_pending_updates=True)
