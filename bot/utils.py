import uuid
import random
import string
import time
from datetime import datetime, timedelta, timezone

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
    now = datetime.now(timezone.utc).date()
    expiry_date = expiry.astimezone(timezone.utc).date()
    return expiry_date == now + timedelta(days=1)

def is_admin(tg_id: int) -> bool:
    from os import getenv
    return str(tg_id) in getenv("ADMIN_ID", "")

def timestamp_to_date(ts: int) -> str:
    try:
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        return "неизвестно"