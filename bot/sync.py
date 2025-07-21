# bot/sync.py

import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from aiogram import Bot
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from .api import get_all_clients
from gspread_formatting import Color

# Загрузка .env
load_dotenv()

SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
SHEET_NAME = os.getenv("SHEET_NAME")
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Цвета подсветки
GREEN = {"red": 0.85, "green": 0.94, "blue": 0.85}
RED   = {"red": 0.96, "green": 0.80, "blue": 0.80}
YELLOW= {"red": 1.0,  "green": 0.98, "blue": 0.8}
BLUE = {"red": 0.8, "green": 0.9, "blue": 1.0}

async def sync_to_google_sheets(bot: Bot):
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).worksheet(SHEET_NAME)

    header = ["TG ID", "Username", "Имя", "Дата начала", "Дата окончания", "Сумма", "Статус"]
    all_rows = sheet.get_all_values()
    existing = {row[0]: row for row in all_rows[1:] if row and row[0]}

    clients = await get_all_clients()
    updates = []
    today_msk = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y")
    now_ts = datetime.now().timestamp() * 1000

    for client_data in clients:
        tg_id_raw = client_data.get("tgId")
        if tg_id_raw is None:
            continue

        tg_id = str(tg_id_raw)
        try:
            user = await bot.get_chat(int(tg_id))
            username = f"@{user.username}" if user.username else "Без username"
        except Exception:
            username = "Не найден"

        comment = client_data.get("comment", "")
        expiry = client_data.get("expiryTime", 0)
        expiry_str = datetime.fromtimestamp(expiry / 1000).strftime("%d.%m.%Y") if expiry else ""

        if expiry == 0:
            status = "Безлимит"
        elif expiry > now_ts:
            status = "Активен"
        else:
            status = "Истёк"

        if expiry_str == today_msk and status == "Активен":
            for admin_id in ADMIN_IDS:
                await bot.send_message(
                    admin_id,
                    f"\u26a0\ufe0f Подписка пользователя {comment} ({username}) истекает сегодня ({expiry_str})"
                )

        old_row = existing.get(tg_id)
        new_row = [tg_id, username, comment, "", expiry_str, "", status]

        if not old_row:
            updates.append(new_row)
        else:
            changed = False
            for i in [1, 2, 4, 6]:
                if len(old_row) <= i or old_row[i] != new_row[i]:
                    changed = True
                    break
            if changed:
                new_row[3] = old_row[3] if len(old_row) > 3 else ""
                new_row[5] = old_row[5] if len(old_row) > 5 else ""
                updates.append(new_row)

    tg_ids_in_sheet = set(existing.keys())
    tg_ids_current = {str(c.get("tgId")) for c in clients if c.get("tgId")}
    removed_ids = tg_ids_in_sheet - tg_ids_current
    print(f"[sync] Обновляем {len(updates)} строк, удалено {len(removed_ids)}")

    result = [header]
    for row in all_rows[1:]:
        tg_id = row[0]
        if tg_id in removed_ids:
            continue
        updated_row = next((r for r in updates if r[0] == tg_id), None)
        result.append(updated_row if updated_row else row)
    for row in updates:
        if row[0] not in tg_ids_in_sheet:
            result.append(row)

    # Очистка и обновление таблицы
    try:
        sheet.batch_clear(["A2:G1000"])
        sheet.update("A1:G1", [header])
        if len(result) > 1:
            sheet.update("A2", result[1:])
    except Exception as e:
        print(f"[sync] \u274c Ошибка при обновлении таблицы: {e}")

    # Подсветка строк по статусу
    try:
        requests = []
        for i, row in enumerate(result[1:], start=2):
            status = row[6].strip().lower() if len(row) > 6 else ""
            expiry_str = row[4].strip() if len(row) > 4 else ""
            color = None

            if status == "активен":
                color = GREEN
            elif status == "истёк":
                color = RED
            elif status == "безлимит":
                color = BLUE
            elif expiry_str == today_msk:
                color = YELLOW

            if color:
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet._properties["sheetId"],
                            "startRowIndex": i - 1,
                            "endRowIndex": i,
                            "startColumnIndex": 0,
                            "endColumnIndex": 7
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": color
                            }
                        },
                        "fields": "userEnteredFormat.backgroundColor"
                    }
                })

        if requests:
            sheet.spreadsheet.batch_update({"requests": requests})

    except Exception as e:
        print(f"[sync] \u26a0\ufe0f Ошибка при применении подсветки: {e}")
