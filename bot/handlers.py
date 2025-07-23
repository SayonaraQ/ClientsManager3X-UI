from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery, ShippingOption, ContentType
from aiogram.enums import ContentType
from aiogram.filters import Command, CommandObject
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from bot.sync import sync_to_google_sheets
import os
from bot.api import find_user_by_tg, add_trial_user, get_inbounds, update_user_expiry, get_all_clients
from bot.utils import generate_uuid, generate_sub_id, generate_email, generate_expiry, get_expiry_datetime, is_admin

router = Router()

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
SUB_LINK_TEMPLATE = os.getenv("SUB_LINK_TEMPLATE")

# /start команда
@router.message(Command("start"))
async def start_handler(message: Message):
    tg_id = message.from_user.id
    user = await find_user_by_tg(tg_id)

    now = datetime.now(ZoneInfo("Europe/Moscow"))
    reply_buttons = [
        [InlineKeyboardButton(text="🔎 Проверить статус", callback_data="check_status")],
        [InlineKeyboardButton(text="💬 Связаться с админом", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]

    if user:
        expiry_ms = user.get("expiryTime")
        expiry_str = "∞"
        expired = False

        if expiry_ms:
            dt = get_expiry_datetime(expiry_ms)
            if dt:
                expiry_str = dt.strftime("%d.%m.%Y %H:%M")
                expired = dt < now

        sub_id = user.get("subId")
        sub_link = SUB_LINK_TEMPLATE.format(subId=sub_id) if sub_id else "Не найдена"

        if expired:
            reply_buttons.insert(0, [InlineKeyboardButton(text="🔁 Продлить подписку", callback_data="renew_subscription")])
            await message.answer(
                "👋 Добро пожаловать!\n"
                f"❌ Ваша подписка истекла <b>{expiry_str}</b>\n\n"
                f"🔗 Ваша ссылка на подключение:\n<code>{sub_link}</code>\n\n"
                "💳 Чтобы снова получить доступ, выберите срок продления подписки:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=reply_buttons)
            )
        else:
            await message.answer(
                "👋 Добро пожаловать!\n"
                f"📅 Ваша подписка активна до: <b>{expiry_str}</b>\n"
                f"🔗 Ваша ссылка для подключения:\n<code>{sub_link}</code>\n\n"
                "⏰ Я напомню о необходимости продления за день до окончания срока действия подписки.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=reply_buttons)
            )

    else:
        trial_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Получить доступ", callback_data="get_trial")],
                [InlineKeyboardButton(text="💬 Связаться с админом", url=f"https://t.me/{ADMIN_USERNAME}")]
            ]
        )
        await message.answer(
            "👋 Привет! Похоже, у вас ещё нет подписки на наш сервис.\n"
            "Хотите получить бесплатный пробный доступ на 3 дня?",
            reply_markup=trial_kb
        )


# Кнопка получения триала
@router.callback_query(F.data == "get_trial")
async def handle_get_trial(callback: CallbackQuery):
    tg_id = callback.from_user.id
    inbounds = await get_inbounds()
    if not inbounds:
        await callback.answer("❌ Не удалось получить информацию. Попробуйте позже.", show_alert=True)
        return

    inbound = inbounds[0]

    success, sub_id, expiry_ms = await add_trial_user(inbound["id"], tg_id)
    if not success:
        await callback.answer("❌ Не удалось создать пробную учетную запись.", show_alert=True)
        return

    expiry = get_expiry_datetime(expiry_ms).strftime("%d.%m.%Y %H:%M")
    sub_link = SUB_LINK_TEMPLATE.format(subId=sub_id)

    await callback.answer()

    await callback.message.answer(
        f"🎉 Ваша пробная подписка активирована!\n\n"
        f"📅 Дата окончания: <b>{expiry}</b>\n\n"
        f"🔗 Ваша ссылка для подключения, СКОПИРУЙТЕ ЕЁ:\n<code>{sub_link}</code>\n\n"
        f"✅ Используйте её в вашем VPN-клиенте.\n"
        f"Инструкция по подключению: https://telegra.ph/Instrukciya-po-nastrojke-nashego-VPN-09-11-2\n\n"
        f"Стоимость подписки после пробного периода — 200р/месяц\n\n"
        f"По любым вопросам можно обращаться к <a href='https://t.me/{ADMIN_USERNAME}'>админу</a>.",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔎 Проверить статус", callback_data="check_status")],
                [InlineKeyboardButton(text="💬 Связаться с админом", url=f"https://t.me/{ADMIN_USERNAME}")]
            ]
        )
    )

# Проверить статус подписки
@router.callback_query(F.data == "check_status")
async def handle_check_status(callback: CallbackQuery):
    tg_id = callback.from_user.id
    user = await find_user_by_tg(tg_id)

    await callback.answer()

    if user:
        expiry_ms = user.get("expiryTime")
        expiry_str = "∞"
        expired = False

        if expiry_ms:
            dt = get_expiry_datetime(expiry_ms)
            if dt:
                expiry_str = dt.strftime("%d.%m.%Y %H:%M")
                now = datetime.now(ZoneInfo("Europe/Moscow"))
                expired = dt < now

        if expired:
            await callback.message.answer(
                "❌ Статус подписки: <b>Истекла</b>\n"
                f"📅 Дата окончания: <b>{expiry_str}</b>\n\n"
                "Чтобы продлить подписку, выберите один из вариантов ниже.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔁 Продлить подписку", callback_data="renew_subscription")],
                        [InlineKeyboardButton(text="💬 Связаться с админом", url=f"https://t.me/{ADMIN_USERNAME}")]
                    ]
                )
            )
        else:
            await callback.message.answer(
                "🔎 Статус подписки: <b>Активна</b>\n"
                f"📅 Дата окончания: <b>{expiry_str}</b>\n\n"
                "❗ Я напомню о необходимости продления за день до окончания подписки.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔁 Продлить подписку", callback_data="renew_subscription")],
                        [InlineKeyboardButton(text="💬 Связаться с админом", url=f"https://t.me/{ADMIN_USERNAME}")]
                    ]
                )
            )
    else:
        await callback.message.answer(
            "❌ У вас нет активной подписки.\n"
            "Чтобы получить доступ, нажмите команду /start.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="💬 Связаться с админом", url=f"https://t.me/{ADMIN_USERNAME}")]
                ]
            )
        )


# Новые кнопки оплаты
@router.callback_query(F.data == "renew_subscription")
async def handle_renew_subscription(callback: CallbackQuery):
    await callback.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 месяц (200₽)", callback_data="buy_1m")],
            [InlineKeyboardButton(text="3 месяца (600₽)", callback_data="buy_3m")],
            [InlineKeyboardButton(text="6 месяцев (1800₽)", callback_data="buy_6m")],
        ]
    )
    await callback.message.answer("💳 Выберите срок продления подписки:", reply_markup=kb)

@router.callback_query(F.data.startswith("buy_"))
async def handle_buy_subscription(callback: CallbackQuery):
    plan = callback.data.split("_")[1]
    prices = {
        "1m": {"amount": 20000, "label": "1 месяц", "months": 1},
        "3m": {"amount": 60000, "label": "3 месяца", "months": 3},
        "6m": {"amount": 180000, "label": "6 месяцев", "months": 6}
    }

    if plan not in prices:
        await callback.answer("❌ Неверный план", show_alert=True)
        return

    await callback.answer()

    price = prices[plan]
    provider_token = os.getenv("PAYMENT_PROVIDER_TOKEN")

    await callback.message.answer_invoice(
        title="Продление подписки",
        description=f"Подписка на {price['label']}",
        provider_token=provider_token,
        currency="RUB",
        prices=[LabeledPrice(label=price["label"], amount=price["amount"])],
        start_parameter="renew_sub",
        payload=f"{callback.from_user.id}_{plan}"
    )

# Обязательный pre-checkout
@router.pre_checkout_query(lambda q: True)
async def pre_checkout(pre_checkout_q: PreCheckoutQuery):
    await pre_checkout_q.answer(ok=True)

# Успешная оплата
@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment_handler(message: Message):
    payload = message.successful_payment.invoice_payload
    try:
        tg_id_str, plan = payload.split("_")
        tg_id = int(tg_id_str)
    except Exception:
        await message.answer("⚠️ Не удалось обработать оплату.")
        return

    months_map = {"1m": 1, "3m": 3, "6m": 6}
    months = months_map.get(plan)
    if not months:
        await message.answer("⚠️ Неизвестный тариф.")
        return

    user = await find_user_by_tg(tg_id)
    if not user:
        await message.answer("⚠️ Пользователь не найден.")
        return

    expiry_now = get_expiry_datetime(user["expiryTime"])
    now = datetime.now(ZoneInfo("Europe/Moscow"))
    if not expiry_now or expiry_now < now:
        expiry_now = now

    new_expiry = expiry_now + timedelta(days=30 * months)
    new_expiry = new_expiry.replace(hour=23, minute=59, second=59, microsecond=0)

    success = await update_user_expiry(
        user["inbound_id"],
        user["client"]["id"],
        int(new_expiry.astimezone(timezone.utc).timestamp() * 1000)
    )

    if success:
        await message.answer(f"✅ Подписка продлена до <b>{new_expiry.strftime('%d.%m.%Y %H:%M')}</b>")
    else:
        await message.answer("❌ Не удалось продлить подписку. Обратитесь к администратору.")

# Рассылка сообщений пользователям
@router.message(Command("broadcast"))
async def handle_broadcast(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав.")
        return

    text = command.args
    if not text:
        await message.answer("❗ Используйте: /broadcast [сообщение]", parse_mode="HTML")
        return

    # Получаем всех пользователей
    clients = await get_all_clients()
    count = 0
    for client in clients:
        tg_id = client.get("tgId")
        if not tg_id:
            continue
        try:
            await message.bot.send_message(tg_id, text)
            count += 1
        except Exception as e:
            print(f"[broadcast] ❌ Не удалось отправить {tg_id}: {e}")

    await message.answer(f"✅ Сообщение отправлено {count} пользователям.")

#google sheets
@router.message(Command("sync"))
async def sync_command(message: Message, bot: Bot):
    await sync_to_google_sheets(bot)
    await message.answer("✅ Синхронизация таблицы завершена.")