import os
import json
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

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
    patterns = [
        r"(.+?)\s+(?:положил|положила|лежит|находится|стоит|висит|храню)\s+(?:в|на|под|за|около|у|рядом)\s+(.+)",
        r"(.+?)\s+(?:в|на|под|за|около|у)\s+(.+)",
        r"(?:положил|положила|убрал|кинул)\s+(.+?)\s+(?:в|на|под|за)\s+(.+)",
    ]
    t = text.lower().strip()
    for p in patterns:
        m = re.match(p, t)
        if m and m.group(2):
            return m.group(1).strip().capitalize(), m.group(2).strip().capitalize()
    parts = t.split(",")
    if len(parts) >= 2:
        return parts[0].strip().capitalize(), parts[1].strip().capitalize()
    return None, None

def build_context(items):
    if not items:
        return "Список вещей пустой."
    lines = "\n".join([f"• {i['name']} → {i['location']}" + (f" ({i['note']})" if i.get('note') else "") for i in items])
    return f"Список вещей в гараже:\n{lines}"

def ask_gemini(question, items):
    context = build_context(items)
    prompt = f"""Ты помощник для гаража. Помогаешь найти где лежат вещи.

{context}

Отвечай коротко на русском языке. Если вещь есть в списке — скажи где лежит. Если нет — скажи что не знаешь.

Вопрос: {question}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "Не удалось получить ответ от ИИ."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    items = load_items()
    
    # Попытка добавить вещь
    name, location = parse_add(text)
    if name and location:
        items.append({"name": name, "location": location, "note": ""})
        save_items(items)
        await update.message.reply_text(f"✅ Сохранено!\n📦 {name}\n📍 {location}")
        return

    # Команды
    if text.lower() in ["/start", "привет", "старт"]:
        await update.message.reply_text(
            "👋 Привет! Я помогу найти вещи в гараже.\n\n"
            "➕ Добавить: «Ключ положил в шкаф»\n"
            "🔍 Найти: «Где ключи?»\n"
            "📋 Список: напишите /list"
        )
        return

    if text.lower() == "/list":
        if not items:
            await update.message.reply_text("📦 Список пустой. Добавьте вещи!")
        else:
            msg = "📋 Все вещи:\n\n" + "\n".join([f"• {i['name']} → {i['location']}" for i in items])
            await update.message.reply_text(msg)
        return

    # ИИ отвечает на вопрос
    reply = ask_gemini(text, items)
    await update.message.reply_text(reply)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.COMMAND, handle_message))
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
