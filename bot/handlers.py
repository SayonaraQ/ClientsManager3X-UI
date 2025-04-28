from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime
import os

from bot.api import find_user_by_tg, add_trial_user, get_inbounds
from bot.utils import get_expiry_datetime

router = Router()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
SUB_LINK_TEMPLATE = os.getenv("SUB_LINK_TEMPLATE")

@router.message(Command("start"))
async def start_handler(message: Message):
    tg_id = message.from_user.id
    user = await find_user_by_tg(tg_id)

    if user:
        expiry_ms = user.get("expiryTime")
        expiry_str = "∞"
        if expiry_ms:
            dt = get_expiry_datetime(expiry_ms)
            if dt:
                expiry_str = dt.strftime("%d.%m.%Y %H:%M")
        await message.answer(
            "👋 Добро пожаловать! Ваша подписка активна.\n"
            f"📅 Дата окончания: <b>{expiry_str}</b>\n\n"
            f"🔔Я напомню о необходимости продления за сутки до истечения срока действия подписки."
        )
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Получить доступ", callback_data="get_trial")]]
        )
        await message.answer(
            "👋 Привет! Похоже, у вас ещё нет подписки на самый лучший VPN.\n"
            "Хотите получить бесплатный пробный доступ на 3 дня?\n",
            reply_markup=kb
        )

@router.callback_query(F.data == "get_trial")
async def handle_get_trial(callback: CallbackQuery):
    tg_id = callback.from_user.id
    inbounds = await get_inbounds()
    if not inbounds:
        await callback.message.answer("❌ Не удалось получить информацию о VPN. Попробуйте позже.")
        return

    inbound = inbounds[0]  # Берем первый доступный inbound

    success, sub_id, expiry_ms = await add_trial_user(inbound["id"], tg_id)
    if not success:
        await callback.message.answer("❌ Не удалось создать пробную учетную запись.")
        return

    expiry = get_expiry_datetime(expiry_ms).strftime("%d.%m.%Y %H:%M")
    sub_link = SUB_LINK_TEMPLATE.format(subId=sub_id)

    await callback.message.answer(
        f"🎉 Ваша пробная подписка активирована!\n\n"
        f"📅 Дата окончания: <b>{expiry}</b>\n"
        f"🔗 Ваша ссылка на подключение, СКОПИРУЙТЕ ЕЁ:\n<code>{sub_link}</code>\n\n"
        f"✅ Используйте её в вашем VPN-клиенте.\n"
        f"Инструкция по подключению: https://telegra.ph/Instrukciya-po-nastrojke-nashego-VPN-09-11-2\n"
        f"Стоимость подписки после пробного периода - 200р/месяц\n\n"
        f"Если возникнут вопросы или понадобится помощь — пишите <a href='https://t.me/{ADMIN_USERNAME}'>админу</a>.",
        disable_web_page_preview=True
    )