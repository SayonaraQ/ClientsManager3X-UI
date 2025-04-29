import os
import aiohttp
import uuid
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from bot.utils import generate_sub_id, generate_expiry, generate_email, generate_uuid

load_dotenv()

XUI_API_URL = os.getenv("XUI_API_URL")
XUI_USERNAME = os.getenv("XUI_USERNAME")
XUI_PASSWORD = os.getenv("XUI_PASSWORD")

cookies = {}
_client_session: Optional[aiohttp.ClientSession] = None

async def get_session() -> aiohttp.ClientSession:
    global _client_session
    if _client_session is None or _client_session.closed:
        _client_session = aiohttp.ClientSession()
    return _client_session

async def login() -> bool:
    global cookies
    session = await get_session()
    async with session.post(
        f"{XUI_API_URL}/login",
        json={"username": XUI_USERNAME, "password": XUI_PASSWORD},
    ) as resp:
        if resp.status == 200:
            cookies = resp.cookies
            print("[api.py] ✅ Успешный логин, cookie сохранена")
            return True
        print(f"[api.py] ❌ Ошибка логина: {resp.status}")
        return False

async def get_inbounds() -> Optional[list[dict]]:
    if not cookies:
        await login()
    session = await get_session()
    async with session.post(f"{XUI_API_URL}/panel/inbound/list", cookies=cookies) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("obj", [])
        print(f"[api.py] ❌ Ошибка при получении inbounds: {resp.status}")
        return None

async def get_all_clients() -> list[dict]:
    clients = []
    inbounds = await get_inbounds()
    if not inbounds:
        return clients
    for inbound in inbounds:
        try:
            settings = json.loads(inbound.get("settings", "{}"))
            for client in settings.get("clients", []):
                client["inbound_id"] = inbound["id"]
                client["inbound_remark"] = inbound["remark"]
                clients.append(client)
        except Exception as e:
            print(f"[api.py] ⚠️ Ошибка в get_all_clients: {e}")
    return clients

async def find_user_by_tg(tg_id: int) -> Optional[Dict[str, Any]]:
    inbounds = await get_inbounds()
    if not inbounds:
        return None
    for inbound in inbounds:
        try:
            settings = json.loads(inbound.get("settings", "{}"))
            for client in settings.get("clients", []):
                if str(client.get("tgId")) == str(tg_id):
                    return {
                        "inbound_id": inbound["id"],
                        "client": client,
                        "subId": client.get("subId"),
                        "expiryTime": client.get("expiryTime"),
                    }
        except Exception as e:
            print(f"[api.py] ⚠️ Ошибка при обработке клиента: {e}")
    return None

async def add_trial_user(inbound_id: int, tg_id: int):
    try:
        # Получаем inbound
        inbounds = await get_inbounds()
        inbound = next((i for i in inbounds if i["id"] == inbound_id), None)
        if not inbound:
            print(f"[api.py] ❌ Inbound с id={inbound_id} не найден")
            return False, None, None

        # Формируем нового клиента
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

        # Преобразуем в строку JSON
        settings = json.dumps({"clients": [client]})

        # Отправляем POST-запрос
        session = await get_session()
        async with session.post(
            f"{XUI_API_URL}/panel/inbound/addClient",
            data={
                "id": inbound["id"],
                "settings": settings
            },
            cookies=cookies,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        ) as resp:
            try:
                result = await resp.json()
                print(f"[api.py] ✅ Результат добавления клиента: {result}")
                return result.get("success", False), client["subId"], client["expiryTime"]
            except Exception as e:
                text = await resp.text()
                print(f"[api.py] ❌ Ошибка при чтении ответа: {e}, текст ответа:\n{text}")
                return False, None, None
    except Exception as e:
        print(f"[api.py] ❌ Ошибка добавления клиента: {e}")
        return False, None, None

async def test_api_connection() -> bool:
    return await login() and (await get_inbounds() is not None)

async def update_user_expiry(inbound_id: int, client_id: str, new_expiry_time: int) -> bool:
    try:
        session = await get_session()
        inbounds = await get_inbounds()
        if not inbounds:
            print("[api.py] ❌ Не удалось получить список inbounds")
            return False

        for inbound in inbounds:
            if inbound["id"] != inbound_id:
                continue

            try:
                settings = json.loads(inbound.get("settings", "{}"))
                for client in settings.get("clients", []):
                    if client.get("id") == client_id:
                        client["expiryTime"] = new_expiry_time

                        payload = {
                            "id": inbound_id,
                            "settings": json.dumps({"clients": [client]})
                        }

                        async with session.post(
                            f"{XUI_API_URL}/panel/inbound/update",
                            data=payload,
                            cookies=cookies,
                            headers={"Content-Type": "application/x-www-form-urlencoded"}
                        ) as resp:
                            text = await resp.text()
                            if resp.status == 200:
                                print(f"[api.py] ✅ Подписка клиента {client_id} успешно продлена.")
                                return True
                            else:
                                print(f"[api.py] ❌ Ошибка продления ({resp.status}): {text}")
                                return False
            except Exception as e:
                print(f"[api.py] ⚠️ Ошибка при обработке inbound: {e}")

        print(f"[api.py] ❌ Клиент с id {client_id} не найден.")
        return False

    except Exception as e:
        print(f"[api.py] ❌ Исключение в update_user_expiry: {e}")
        return False
