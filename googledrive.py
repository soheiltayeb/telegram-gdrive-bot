import os
import logging
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# دریافت متغیرهای محیطی
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not GOOGLE_CREDENTIALS:
    raise Exception("❌ GOOGLE_CREDENTIALS not found in environment variables")
if not TELEGRAM_BOT_TOKEN:
    raise Exception("❌ TELEGRAM_BOT_TOKEN not found in environment variables")

# بارگذاری اعتبارنامه گوگل درایو
creds = Credentials.from_service_account_info(json.loads(GOOGLE_CREDENTIALS))
drive_service = build('drive', 'v3', credentials=creds)

# تنظیمات لاگ‌گیری
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# دستور شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('سلام! فایل خود را ارسال کنید تا در گوگل درایو آپلود شود.')

# مدیریت فایل‌های ارسالی
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_name = update.message.document.file_name
    file_path = f'downloads/{file_name}'

    # ساخت پوشه دانلود
    os.makedirs('downloads', exist_ok=True)

    # دانلود فایل
    await file.download(file_path)
    await update.message.reply_text('✅ فایل دریافت شد. در حال آپلود...')

    # آپلود به گوگل درایو
    file_metadata = {'name': file_name}
    media = MediaFileUpload(file_path, resumable=True)
    uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    # ایجاد لینک دانلود
    file_id = uploaded_file.get('id')
    drive_service.permissions().create(fileId=file_id, body={'role': 'reader', 'type': 'anyone'}).execute()
    file_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

    # ارسال لینک به کاربر
    await update.message.reply_text(f'✅ فایل آپلود شد! لینک دانلود:\n{file_link}')

    # حذف فایل محلی
    os.remove(file_path)

# راه‌اندازی ربات
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    logger.info("🚀 ربات اجرا شد...")
    app.run_polling()

if __name__ == '__main__':
    main()
