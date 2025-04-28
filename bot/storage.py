import os
import shutil
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR = os.getenv("FILES_DIR", "./data/uploads")
ADMIN_IDS = [int(uid) for uid in os.getenv("ADMIN_ID", "").split(",") if uid.strip().isdigit()]

def ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)

def generate_filename(user_id: int, original_filename: str = "file") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{user_id}_{timestamp}_{original_filename}"

async def save_user_file(message: Message) -> str:
    ensure_upload_dir()
    document = message.document or message.photo[-1]  # поддержка файлов и фото
    filename = generate_filename(message.from_user.id, document.file_name if hasattr(document, "file_name") else "image.jpg")
    file_path = os.path.join(UPLOAD_DIR, filename)

    await document.download(destination=file_path)
    return file_path

async def notify_admins(bot, file_path: str, user_id: int, caption: str = None):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_document(
                chat_id=admin_id,
                document=open(file_path, "rb"),
                caption=caption or f"📩 Новый файл от пользователя {user_id}",
            )
        except Exception as e:
            print(f"[STORAGE] ❌ Ошибка отправки файла админу {admin_id}: {e}")

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_admin_keyboard(tg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Продлить", callback_data=f"extend_{tg_id}")]
    ])