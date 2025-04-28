import uuid
import random
import string
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

def generate_uuid() -> str:
    return str(uuid.uuid4())

def generate_sub_id() -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def generate_email(tg_id: int) -> str:
    return f"trial_{tg_id}"

def generate_expiry(days: int = 3) -> int:
    """Генерирует дату истечения подписки через N дней в 23:59:59 по московскому времени"""
    now_msk = datetime.now(ZoneInfo("Europe/Moscow"))
    target_date = (now_msk + timedelta(days=days)).replace(
        hour=23, minute=59, second=59, microsecond=0
    )
    target_date_utc = target_date.astimezone(timezone.utc)
    return int(target_date_utc.timestamp() * 1000)

def get_expiry_datetime(ms: int) -> datetime:
    """Преобразует метку времени в datetime по московскому времени"""
    try:
        return datetime.fromtimestamp(ms / 1000, tz=ZoneInfo("Europe/Moscow"))
    except Exception:
        return None

def is_expiring_soon(expiry: datetime) -> bool:
    """Проверяет, истекает ли подписка сегодня или завтра"""
    now_msk = datetime.now(ZoneInfo("Europe/Moscow"))
    today = now_msk.date()
    tomorrow = today + timedelta(days=1)
    return expiry.date() in (today, tomorrow)

def is_admin(tg_id: int) -> bool:
    from os import getenv
    return str(tg_id) in getenv("ADMIN_ID", "")

def timestamp_to_date(ts: int) -> str:
    try:
        dt = datetime.fromtimestamp(ts / 1000, tz=ZoneInfo("Europe/Moscow"))
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return "неизвестно"
