import os
import logging
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json


if "GOOGLE_CREDENTIALS" in os.environ:
    print("متغیر محیطی تنظیم شده است.")
else:
    print("متغیر محیطی یافت نشد.")

print("GOOGLE_CREDENTIALS:", os.getenv("GOOGLE_CREDENTIALS"))


credentials_json = os.getenv("GOOGLE_CREDENTIALS")
if credentials_json:
    creds = json.loads(credentials_json)
else:
    raise Exception("GOOGLE_CREDENTIALS not found in environment variables")


# لاگ‌گیری
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# توکن ربات تلگرام
TELEGRAM_BOT_TOKEN = '7685688487:AAHBtY6Gol0X4JjvcDAODxa34X4gWyXaNFQ'

# لود کردن اعتبارنامه گوگل
creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive.file'])

# ساخت سرویس گوگل درایو
drive_service = build('drive', 'v3', credentials=creds, cache_discovery=False)


# دستور شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('سلام! فایل خود را برای آپلود به گوگل درایو ارسال کنید.')

# مدیریت فایل‌های ارسالی
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_name = update.message.document.file_name
    file_path = f'downloads/{file_name}'

    # ساخت پوشه دانلود (در صورت نبود)
    os.makedirs('downloads', exist_ok=True)

    # دانلود فایل
    await file.download_to_drive(file_path)
    await update.message.reply_text('فایل دریافت شد. در حال آپلود...')

    # آپلود به گوگل درایو
    file_metadata = {'name': file_name}
    media = MediaFileUpload(file_path, resumable=True)
    uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    # ایجاد لینک دانلود
    file_id = uploaded_file.get('id')
    drive_service.permissions().create(fileId=file_id, body={'role': 'reader', 'type': 'anyone'}).execute()
    file_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

    # ارسال لینک به کاربر
    await update.message.reply_text(f'فایل آپلود شد! لینک دانلود:\n{file_link}')

    # حذف فایل محلی
    os.remove(file_path)

# راه‌اندازی ربات
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    logger.info("ربات اجرا شد...")
    app.run_polling()

if __name__ == '__main__':
    main()
