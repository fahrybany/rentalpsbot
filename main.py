import os
import json
import logging
from datetime import datetime
from flask import Flask
from threading import Thread

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# === SETUP ENVIRONMENT ===
TELEGRAM_TOKEN = os.environ["BOT_TOKEN"]
SPREADSHEET_ID = os.environ["SHEET_ID"]
creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)

gc = gspread.authorize(creds)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
drive = build("drive", "v3", credentials=creds)

# === STATE MACHINE ===
NAMA, NOMINAL, JENIS, QRIS, CASH, KETERANGAN, FOTO = range(7)
user_data = {}

# === FLASK KEEP ALIVE ===
app = Flask(__name__)
@app.route('/')
def index():
    return "Bot hidup bro (Render version)"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Ketik /lapor untuk kirim laporan harian ya.")

async def lapor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Siapa nama kamu hari ini?")
    return NAMA

async def input_nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data["nama"] = update.message.text
    await update.message.reply_text("Total nominal transaksi hari ini?")
    return NOMINAL

async def input_nominal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data["nominal"] = update.message.text
    await update.message.reply_text("Ini laporan 'pengeluaran' atau 'pendapatan'?")
    return JENIS

async def input_jenis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data["jenis"] = update.message.text
    await update.message.reply_text("Berapa via QRIS?")
    return QRIS

async def input_qris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data["qris"] = update.message.text
    await update.message.reply_text("Berapa via CASH?")
    return CASH

async def input_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data["cash"] = update.message.text
    await update.message.reply_text("Keterangan tambahan?")
    return KETERANGAN

async def input_keterangan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data["keterangan"] = update.message.text
    await update.message.reply_text("Upload foto bon sekarang ya (wajib bro)!")
    return FOTO

async def input_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    filename = f"bon_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    await file.download_to_drive(filename)

    # Upload ke Google Drive
    file_metadata = {'name': filename}
    media = MediaFileUpload(filename, mimetype='image/jpeg')
    upload = drive.files().create(body=file_metadata, media_body=media, fields='id').execute()
    drive_link = f"https://drive.google.com/file/d/{upload['id']}"

    # Simpan ke Google Sheet
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_data['nama'],
        user_data['jenis'],
        user_data['nominal'],
        user_data['qris'],
        user_data['cash'],
        user_data['keterangan'],
        drive_link
    ])

    await update.message.reply_text("Laporan berhasil dicatat. Makasih!")

    os.remove(filename)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Laporan dibatalkan.")
    return ConversationHandler.END

# === MAIN ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    Thread(target=run_flask).start()

    app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("lapor", lapor)],
        states={
            NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_nama)],
            NOMINAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_nominal)],
            JENIS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_jenis)],
            QRIS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_qris)],
            CASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_cash)],
            KETERANGAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_keterangan)],
            FOTO: [MessageHandler(filters.PHOTO, input_foto)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(conv_handler)

    print("Bot jalan bro! CTRL+C buat stop.")
    app_bot.run_polling()
