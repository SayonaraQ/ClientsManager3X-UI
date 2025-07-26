import os
import random
import string
import gspread
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
SHEET_TAB = os.getenv("SHEET_TAB_REF")
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")


# Генерация уникального кода
def generate_ref_code(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


# Получить ref_code пользователя, или создать новый
def get_or_create_ref_code(tg_id: int) -> str:
    gc = gspread.service_account(filename=CREDENTIALS_PATH)
    sh = gc.open(SPREADSHEET_NAME)
    ws = sh.worksheet(SHEET_TAB)

    all_rows = ws.get_all_values()
    for row in all_rows:
        if row[0] == str(tg_id):
            return row[2]  # ref_code уже есть

    new_code = generate_ref_code()
    ws.append_row([str(tg_id), "", new_code, datetime.now().strftime("%Y-%m-%d %H:%M"), ""])
    return new_code


# Сохранить связь только если её ещё нет
def save_referral(inviter_tg_id: int, invited_tg_id: int, ref_code: str):
    gc = gspread.service_account(filename=CREDENTIALS_PATH)
    sh = gc.open(SPREADSHEET_NAME)
    ws = sh.worksheet(SHEET_TAB)

    all_rows = ws.get_all_values()
    for row in all_rows:
        if row[1] == str(invited_tg_id):
            return  # уже записан как приглашённый — ничего не делаем

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([str(inviter_tg_id), str(invited_tg_id), ref_code, now, "Нет бонуса"])


# Получить всех приглашённых
def get_referrals_by_inviter(inviter_tg_id: int) -> list[dict]:
    gc = gspread.service_account(filename=CREDENTIALS_PATH)
    sh = gc.open(SPREADSHEET_NAME)
    ws = sh.worksheet(SHEET_TAB)

    rows = ws.get_all_values()
    result = []

    for row in rows:
        if row[0] == str(inviter_tg_id) and row[1]:
            result.append({
                "tg_id": row[1],
                "date": row[3],
                "bonus": row[4] if len(row) >= 5 else ""
            })
    return result


# Общий метод отправки ссылки
async def send_referral_link(bot, user_id, chat_id):
    ref_code = get_or_create_ref_code(user_id)
    bot_name = os.getenv("BOT_USERNAME")
    ref_link = f"https://t.me/{bot_name}?start=ref_{ref_code}"
    await bot.send_message(
        chat_id,
        f"👥 Пригласите друзей и получите бонусы!\n"
        f"Ваша реферальная ссылка:\n\n<code>{ref_link}</code>\n\n"
        f"🎁 5 приглашённых и оплативших подписку друзей = 1 месяц бесплатно для тебя\n"
        f"🎁 10 — 2 месяца и т.д.",
        parse_mode="HTML"
    )
