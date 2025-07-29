import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot hidup bro (Render version)"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo bro! Bot lo udah nyala nih di Render!")

if __name__ == '__main__':
    from telegram.ext import ApplicationBuilder
    import logging

    logging.basicConfig(level=logging.INFO)
    Thread(target=run_flask).start()
    
    app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.run_polling()
