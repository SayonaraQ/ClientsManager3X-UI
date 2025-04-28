import uuid
import random
import string
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

def generate_uuid() -> str:
    return str(uuid.uuid4())

def generate_sub_id() -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def generate_email(tg_id: int) -> str:
    return f"trial_{tg_id}"

def generate_expiry(days: int = 3) -> int:
    return int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp() * 1000)

def get_expiry_datetime(ms: int) -> datetime:
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    except Exception:
        return None

def is_expiring_soon(expiry: datetime) -> bool:
    """ Проверка: истекает сегодня или завтра """
    now_msk = datetime.now(ZoneInfo("Europe/Moscow"))
    expiry_msk = expiry.astimezone(ZoneInfo("Europe/Moscow"))

    today = now_msk.date()
    tomorrow = today + timedelta(days=1)

    return expiry_msk.date() in (today, tomorrow)

def is_admin(tg_id: int) -> bool:
    from os import getenv
    return str(tg_id) in getenv("ADMIN_ID", "")

def timestamp_to_date(ts: int) -> str:
    try:
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).astimezone(ZoneInfo("Europe/Moscow"))
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return "неизвестно"