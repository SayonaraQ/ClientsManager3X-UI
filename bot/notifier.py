# bot/notifier.py
from aiogram import Bot
from datetime import datetime, timezone
from bot.api import get_all_clients
from bot.utils import get_expiry_datetime, is_expiring_soon
import os

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")  # Должен быть задан в .env без @

async def notify_users(bot: Bot):
    try:
        clients = await get_all_clients()
        notified = 0

        for client in clients:
            tg_id = client.get("tgId")
            expiry_ms = client.get("expiryTime")

            if not tg_id or not expiry_ms:
                continue

            expiry = get_expiry_datetime(expiry_ms)
            if not expiry or not is_expiring_soon(expiry):
                continue

            try:
                await bot.send_message(
                    chat_id=tg_id,
                    text=(
                        "⚠️ <b>Ваша подписка скоро закончится!</b>\n\n"
                        f"📅 Дата окончания: <b>{expiry.strftime('%d.%m.%Y %H:%M')}</b>\n\n"
                        f"💬 Чтобы продлить доступ, напишите <a href='https://t.me/{ADMIN_USERNAME}'>админу</a>."
                    ),
                    disable_web_page_preview=True
                )
                notified += 1
            except Exception as e:
                print(f"[NOTIFIER] ❌ Ошибка при отправке уведомления пользователю {tg_id}: {e}")

        print(f"[NOTIFIER] ✅ Уведомлено пользователей: {notified}")

    except Exception as e:
        print(f"[NOTIFIER] ❌ Ошибка при выполнении уведомлений: {e}")