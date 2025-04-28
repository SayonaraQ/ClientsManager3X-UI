import asyncio
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from dotenv import load_dotenv

from bot.handlers import router
from bot.notifier import notify_users
from bot.api import test_api_connection

# Загрузка переменных из .env
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
XUI_API_URL = os.getenv("XUI_API_URL")
XUI_USERNAME = os.getenv("XUI_USERNAME")
XUI_PASSWORD = os.getenv("XUI_PASSWORD")

print("🔧 DEBUG ENV:", TOKEN, XUI_API_URL, XUI_USERNAME)

if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не задан в .env")

if not all([XUI_API_URL, XUI_USERNAME, XUI_PASSWORD]):
    raise RuntimeError("❌ Переменные XUI_API_URL, XUI_USERNAME и XUI_PASSWORD должны быть заданы в .env")

# Инициализация бота с HTML-парсингом
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Инициализация диспетчера
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

# Установка команд бота
async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу"),
    ])

# Проверка API перед стартом
async def log_api_info():
    print("\n🛠 [main.py] Проверка подключения к API 3x-ui:")
    try:
        result = await test_api_connection()
        if result:
            print(" → ✅ Успешное подключение к API")
        else:
            print(" → ❌ Не удалось получить список inbounds")
    except Exception as e:
        print(f" → ❌ Ошибка при обращении к API: {e}")

# Фоновая задача — уведомление пользователей в 18:00 по МСК
async def periodic_notifications(bot: Bot):
    while True:
        now = datetime.now(ZoneInfo("Europe/Moscow"))
        target = now.replace(hour=18, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        print(f"⏳ Ждём до 18:00 по МСК: {wait_seconds / 3600:.2f} ч.")
        await asyncio.sleep(wait_seconds)

        print("🔔 Запуск уведомлений...")
        await notify_users(bot)

# Точка входа
async def main():
    print("✅ Бот запускается...")
    await log_api_info()
    await set_commands()
    asyncio.create_task(periodic_notifications(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())