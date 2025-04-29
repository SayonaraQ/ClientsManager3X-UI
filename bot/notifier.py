# bot/notifier.py
import os
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from zoneinfo import ZoneInfo
from bot.api import get_all_clients
from bot.utils import get_expiry_datetime, is_expiring_soon

# Загружаем данные из .env
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_GREETING_TEXT = os.getenv("ADMIN_GREETING_TEXT")

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
                # Переводим дату окончания в московское время
                expiry_msk = expiry.astimezone(ZoneInfo("Europe/Moscow"))

                # Создаем кнопки
                button = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔁 Продлить подписку", callback_data="renew_subscription")],
                        [InlineKeyboardButton(
                            text="💬 Связаться с админом",
                            url=f"tg://resolve?domain={ADMIN_USERNAME}&text={ADMIN_GREETING_TEXT.replace(' ', '%20')}"
                        )]
                    ]
                )

                await bot.send_message(
                    chat_id=tg_id,
                    text=(
                        "⚠️ <b>Ваша подписка скоро закончится!</b>\n\n"
                        f"📅 Дата окончания: <code>{expiry_msk.strftime('%d.%m.%Y %H:%M')}</code>\n\n"
                        "💬 Чтобы продлить доступ, нажмите одну из кнопок ниже."
                    ),
                    reply_markup=button
                )
                notified += 1
            except Exception as e:
                print(f"[NOTIFIER] ❌ Ошибка при отправке уведомления пользователю {tg_id}: {e}")

        print(f"[NOTIFIER] ✅ Уведомлено пользователей: {notified}")

    except Exception as e:
        print(f"[NOTIFIER] ❌ Ошибка при выполнении уведомлений: {e}")
