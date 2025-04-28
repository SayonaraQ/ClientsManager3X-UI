from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime, timedelta
import os

from bot.api import find_user_by_tg, add_trial_user, get_inbounds, prolong_user
from bot.utils import generate_uuid, generate_sub_id, generate_email, generate_expiry, get_expiry_datetime, is_admin

router = Router()

ADMIN_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Куда уведомлять админа
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
SUB_LINK_TEMPLATE = os.getenv("SUB_LINK_TEMPLATE")

YOOMONEY_LINKS = {
    "1": os.getenv("YOOMONEY_LINK_1"),
    "3": os.getenv("YOOMONEY_LINK_3"),
    "6": os.getenv("YOOMONEY_LINK_6")
}

# /start команда
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
            f"📅 Дата окончания: <b>{expiry_str}</b>\n"
            "Я напомню вам о необходимости продления за сутки до истечения срока действия подписки."
        )
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Получить доступ", callback_data="get_trial")]
            ]
        )
        await message.answer(
            "👋 Привет! Похоже, у вас ещё нет подписки на наш VPN.\n"
            "Хотите получить бесплатный пробный доступ на 3 дня?",
            reply_markup=kb
        )

# Кнопка получения триала
@router.callback_query(F.data == "get_trial")
async def handle_get_trial(callback: CallbackQuery):
    tg_id = callback.from_user.id
    inbounds = await get_inbounds()
    if not inbounds:
        await callback.message.answer("❌ Не удалось получить информацию о VPN. Попробуйте позже.")
        return

    inbound = inbounds[0]
    client = {
        "id": generate_uuid(),
        "email": generate_email(tg_id),
        "enable": True,
        "expiryTime": generate_expiry(),
        "flow": "xtls-rprx-vision",
        "limitIp": 2,
        "reset": 0,
        "tgId": tg_id,
        "subId": generate_sub_id()
    }

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
        f"Если возникнут вопросы — пишите <a href='https://t.me/{ADMIN_USERNAME}'>админу</a>.",
        disable_web_page_preview=True
    )

# Кнопка "Продлить подписку" (первый этап)
async def send_payment_options(tg_id: int, bot):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 месяц (200₽)", callback_data="pay_1"),
                InlineKeyboardButton(text="3 месяца (600₽)", callback_data="pay_3"),
                InlineKeyboardButton(text="6 месяцев (1200₽)", callback_data="pay_6"),
            ]
        ]
    )
    await bot.send_message(
        chat_id=tg_id,
        text="💳 Выберите срок продления подписки:",
        reply_markup=kb
    )

# Обработка выбора срока оплаты
@router.callback_query(F.data.startswith("pay_"))
async def handle_payment_choice(callback: CallbackQuery):
    choice = callback.data.split("_")[1]

    link = YOOMONEY_LINKS.get(choice)
    if not link:
        await callback.answer("❌ Ошибка, неверный вариант оплаты.")
        return

    # Отправляем ссылку для оплаты и кнопку "✅ Подтвердить оплату"
    await callback.message.answer(
        text=f"💸 Перейдите по ссылке для оплаты:\n{link}\n\n"
             "После оплаты нажмите кнопку <b>✅ Подтвердить оплату</b>.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data="payment_done")]
            ]
        )
    )

# Обработка "✅ Подтвердить оплату"
@router.callback_query(F.data == "payment_done")
async def handle_payment_done(callback: CallbackQuery):
    tg_id = callback.from_user.id
    username = callback.from_user.username or "Без username"

    await callback.message.edit_reply_markup()  # Удаляем кнопки

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Продлить на 1 месяц", callback_data=f"extend_1_{tg_id}"),
                InlineKeyboardButton(text="Продлить на 3 месяца", callback_data=f"extend_3_{tg_id}"),
                InlineKeyboardButton(text="Продлить на 6 месяцев", callback_data=f"extend_6_{tg_id}"),
            ]
        ]
    )

    await callback.message.answer("✅ Спасибо! Ваше подтверждение отправлено администратору.")

    await callback.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=(
            f"👤 Пользователь @{username} подтвердил оплату.\n"
            f"Telegram ID: <code>{tg_id}</code>\n\n"
            "Выберите срок продления:"
        ),
        reply_markup=kb
    )

# Обработка продления админом
@router.callback_query(F.data.startswith("extend_"))
async def handle_extend(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    parts = callback.data.split("_")
    months = int(parts[1])
    tg_id = int(parts[2])

    user = await find_user_by_tg(tg_id)
    if not user:
        await callback.message.answer("❌ Пользователь не найден.")
        return

    expiry_now = get_expiry_datetime(user["expiryTime"])
    if not expiry_now:
        expiry_now = datetime.now()

    # Новая дата истечения
    new_expiry = expiry_now + timedelta(days=30 * months)
    new_expiry = new_expiry.replace(hour=23, minute=59, second=59, microsecond=0)

    success = await prolong_user(user["client"]["id"], int(new_expiry.timestamp() * 1000))

    await callback.message.edit_reply_markup()  # Удаляем кнопки

    if success:
        await callback.message.answer(
            f"✅ Подписка пользователя <code>{tg_id}</code> продлена до {new_expiry.strftime('%d.%m.%Y %H:%M:%S')}"
        )
    else:
        await callback.message.answer(f"❌ Ошибка при продлении пользователя <code>{tg_id}</code>.")
