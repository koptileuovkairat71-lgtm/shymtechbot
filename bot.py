import os
import json
import requests
from telegram import Update
from telegram.ext import Updater, MessageHandler, filters, CommandHandler, CallbackContext

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
        r"(.+?)\s+(?:положил|положила|лежит|находится|стоит|висит|храню)\s+(?:в|на|под|за|около|у|рядом)\s+(.+)",
        r"(?:положил|положила|убрал|кинул)\s+(.+?)\s+(?:в|на|под|за)\s+(.+)",
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
    prompt = f"""{context}

Отвечай коротко на русском. Если вещь есть — скажи где лежит. Если нет — скажи что не знаешь.

Вопрос: {question}"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "Ошибка ИИ. Попробуйте ещё раз."

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Привет! Я помогу найти вещи в гараже.\n\n"
        "➕ Добавить: «Ключ положил в шкаф»\n"
        "🔍 Найти: «Где ключи?»\n"
        "📋 Список всего: /list"
    )

def list_items(update: Update, context: CallbackContext):
    items = load_items()
    if not items:
        update.message.reply_text("📦 Список пустой. Добавьте вещи!")
    else:
        msg = "📋 Все вещи:\n\n" + "\n".join([f"• {i['name']} → {i['location']}" for i in items])
        update.message.reply_text(msg)

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    items = load_items()
    name, location = parse_add(text)
    if name and location:
        items.append({"name": name, "location": location})
        save_items(items)
        update.message.reply_text(f"✅ Сохранено!\n📦 {name}\n📍 {location}")
        return
    reply = ask_gemini(text, items)
    update.message.reply_text(reply)

def main():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("list", list_items))
    dp.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
