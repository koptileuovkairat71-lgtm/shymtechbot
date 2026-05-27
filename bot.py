import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    # Код берет ключи именно из Railway
    gemini_key = os.environ.get("GEMINI_KEY")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={gemini_key}"
    payload = {"contents": [{"parts": [{"text": user_text}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        reply = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        reply = "Ошибка связи с ИИ. Проверьте GEMINI_KEY в Railway."
        
    await update.message.reply_text(reply)

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ.get("TELEGRAM_TOKEN")).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
