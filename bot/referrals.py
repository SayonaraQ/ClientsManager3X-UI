import os
import random
import string
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional
import gspread

load_dotenv()
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
SHEET_TAB = os.getenv("SHEET_TAB_REF")
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")

DB_PATH = "referrals.db"


# Подключение к SQLite
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            inviter_tg_id TEXT,
            invited_tg_id TEXT,
            ref_code TEXT,
            created_at TEXT,
            bonus_status TEXT DEFAULT 'Нет бонуса'
        )
    ''')
    return conn


# Генерация уникального кода
def generate_ref_code(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


# Получить ref_code пользователя, или создать новый
def get_or_create_ref_code(tg_id: int) -> str:
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT ref_code FROM referrals WHERE inviter_tg_id = ? AND invited_tg_id IS NULL", (str(tg_id),))
    row = cursor.fetchone()
    if row:
        conn.close()
        return row[0]

    ref_code = generate_ref_code()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "INSERT INTO referrals (inviter_tg_id, invited_tg_id, ref_code, created_at) VALUES (?, NULL, ?, ?)",
        (str(tg_id), ref_code, now)
    )
    conn.commit()
    conn.close()
    return ref_code


# Сохранить связь только если её ещё нет
def save_referral(inviter_tg_id: int, invited_tg_id: int, ref_code: str):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM referrals WHERE invited_tg_id = ?", (str(invited_tg_id),))
    if cursor.fetchone():
        conn.close()
        return  # Уже записан как приглашённый

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "INSERT INTO referrals (inviter_tg_id, invited_tg_id, ref_code, created_at) VALUES (?, ?, ?, ?)",
        (str(inviter_tg_id), str(invited_tg_id), ref_code, now)
    )
    conn.commit()
    conn.close()


# Получить всех приглашённых
def get_referrals_by_inviter(inviter_tg_id: int) -> list[dict]:
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT invited_tg_id, created_at, bonus_status FROM referrals WHERE inviter_tg_id = ? AND invited_tg_id IS NOT NULL", (str(inviter_tg_id),))
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "tg_id": row[0],
            "date": row[1],
            "bonus": row[2]
        })
    return result


# Отправить пользователю его ссылку
async def send_referral_link(bot, user_id, chat_id):
    ref_code = get_or_create_ref_code(user_id)
    bot_name = os.getenv("BOT_USERNAME")
    ref_link = f"t.me/{bot_name}?start=ref_{ref_code}"
    await bot.send_message(
        chat_id,
        f"👥 Пригласите друзей и получите бонусы!\n"
        f"Ваша реферальная ссылка:\n\n<code>{ref_link}</code>\n\n"
        f"🎁 5 приглашённых и оплативших подписку друзей = 1 месяц бесплатно для тебя\n"
        f"🎁 10 — 2 месяца и т.д.",
        parse_mode="HTML"
    )

async def export_to_gsheet():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM referrals WHERE invited_tg_id IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()

    gc = gspread.service_account(filename=CREDENTIALS_PATH)
    sh = gc.open(SPREADSHEET_NAME)
    ws = sh.worksheet(SHEET_TAB)
    ws.clear()
    ws.append_row(["inviter_tg_id", "invited_tg_id", "ref_code", "created_at", "bonus_status"])

    for row in rows:
        ws.append_row([str(col) if col is not None else "" for col in row])

def get_inviter_by_code(ref_code: str) -> Optional[int]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT inviter_tg_id FROM referrals WHERE ref_code = ? LIMIT 1", (ref_code,))
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None
