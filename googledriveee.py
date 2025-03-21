import os
import logging
import json
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# دریافت متغیرهای محیطی
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")  # اختیاری

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
    await update.message.reply_text(
        "سلام! فایل خود را ارسال کنید تا در گوگل درایو آپلود شود.\n"
        "📌 اگر فایل شما بالای 50MB باشد، باید لینک عمومی آن را ارسال کنید."
    )

# مدیریت فایل‌های ارسالی
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file = update.message.document
        file_id = file.file_id
        file_name = file.file_name
        file_size = file.file_size

        logger.info(f"📥 دریافت فایل: {file_name} ({file_size / 1024 / 1024:.2f} MB)")

        # بررسی حجم فایل
        if file_size > 50 * 1024 * 1024:
            await update.message.reply_text(
                "❌ تلگرام اجازه دانلود مستقیم فایل‌های بالای 50MB را نمی‌دهد.\n"
                "🔹 لطفاً فایل را به @GetPublicLinkBot ارسال کنید و لینک آن را اینجا بفرستید. 📎"
            )
            return

        # دریافت مسیر فایل از تلگرام
        file_info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
        response = requests.get(file_info_url).json()

        if "result" not in response:
            await update.message.reply_text("❌ خطایی در دریافت لینک فایل از تلگرام رخ داد.")
            return

        file_path = response["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

        await update.message.reply_text("✅ لینک دریافت شد. در حال دانلود و آپلود به گوگل درایو...")

        # دانلود فایل و آپلود به گوگل درایو
        file_stream = requests.get(download_url, stream=True)
        media = MediaIoBaseUpload(io.BytesIO(file_stream.content), mimetype="application/octet-stream", resumable=True)

        file_metadata = {"name": file_name}
        if FOLDER_ID:
            file_metadata["parents"] = [FOLDER_ID]

        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        # دریافت لینک دانلود
        uploaded_file_id = uploaded_file.get("id")
        drive_service.permissions().create(fileId=uploaded_file_id, body={"role": "reader", "type": "anyone"}).execute()
        file_link = f"https://drive.google.com/file/d/{uploaded_file_id}/view?usp=sharing"

        logger.info(f"✅ آپلود شد: {file_link}")

        # ارسال لینک به کاربر
        await update.message.reply_text(f'✅ فایل آپلود شد! لینک دانلود:\n{file_link}')

    except Exception as e:
        logger.error(f"❌ خطای عمومی: {e}")
        await update.message.reply_text("❌ مشکلی پیش آمد. لطفاً دوباره تلاش کنید.")

# مدیریت لینک‌های ارسال‌شده توسط کاربر
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = update.message.text
        if "http" not in url or "telegram" not in url:
            await update.message.reply_text("❌ لطفاً یک لینک معتبر تلگرام ارسال کنید.")
            return

        await update.message.reply_text("🔄 در حال دانلود و آپلود به گوگل درایو...")

        # دانلود فایل از لینک
        file_stream = requests.get(url, stream=True)
        file_name = url.split("/")[-1]  # استخراج نام فایل از لینک
        media = MediaIoBaseUpload(io.BytesIO(file_stream.content), mimetype="application/octet-stream", resumable=True)

        file_metadata = {"name": file_name}
        if FOLDER_ID:
            file_metadata["parents"] = [FOLDER_ID]

        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        # تنظیم دسترسی عمومی
        file_id = uploaded_file.get("id")
        drive_service.permissions().create(fileId=file_id, body={"role": "reader", "type": "anyone"}).execute()
        file_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

        await update.message.reply_text(f"✅ فایل آپلود شد!\n📎 لینک دانلود: {file_link}")

    except Exception as e:
        await update.message.reply_text("❌ مشکلی پیش آمد. لطفاً دوباره تلاش کنید.")

# راه‌اندازی ربات
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))  # هندلر لینک

    logger.info("🚀 ربات اجرا شد...")
    app.run_polling()

if __name__ == '__main__':
    main()
