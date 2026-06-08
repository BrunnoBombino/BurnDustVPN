import os
import pickle
import uuid
import secrets
import string
import requests
import json
from core import auth
from pathlib import Path
from datetime import datetime, timezone, timedelta

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class API:
    def __init__(self) -> None:
        # Инициализируем объект сессии requests
        self.ses = requests.Session()

        # Корневая директория и пути к файлам
        self.base_dir = Path(__file__).resolve().parent.parent
        self.backup_path = self.base_dir / "backup_lost_users.txt"

        # Настройки авторизации
        self.host = getattr(auth, 'HOST', '')
        self.API_TOKEN = getattr(auth, 'API_TOKEN', '')

    def connect(self) -> bool:
        if hasattr(auth, 'API_TOKEN') and self.API_TOKEN:
            self.ses.headers.update({"Authorization": f"Bearer {self.API_TOKEN}"})
            return True
        return False

    def save_json_data(self, data: dict, filename: str = "users.json") -> None:
        """
        Сохраняет бэкап-данные в JSON-файл внутри корневой директории проекта.
        """
        # Путь автоматически строится относительно корня проекта
        full_path = self.base_dir / filename

        try:
            with open(full_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            print(f"✅ Бэкап успешно сохранен в: {full_path}")
        except IOError as e:
            print(f"❌ Ошибка записи json в файл {full_path}: {e}")

    def users(self) -> dict:
        """Получает список инбаундов с использованием API токена."""
        if not self.connect():
            return {"success": False, "msg": "API токен не настроен в auth.py"}

        try:
            # Делаем запрос к панели без проверки SSL-сертификата
            url = f"{self.host.rstrip('/')}/panel/api/inbounds/list"
            response = self.ses.get(url, timeout=10, verify=False)

            # Проверка прав доступа
            if response.status_code in (401, 403):
                print("❌ Ошибка: Панель отклонила API токен. Проверьте API_TOKEN.")
                return {"success": False, "msg": f"Ошибка авторизации (Статус {response.status_code})"}

            if response.status_code != 200:
                print(f"❌ Непредвиденная ошибка сервера. Статус-код: {response.status_code}")
                return {"success": False, "msg": f"Ошибка HTTP {response.status_code}"}

            # Проверка типа контента (ожидаем строго JSON)
            content_type = response.headers.get("Content-Type", "").lower()
            if not response.text.strip() or "html" in content_type:
                print("❌ Ошибка: Сервер вернул HTML или пустой ответ вместо JSON.")
                return {"success": False, "msg": "Невалидный ответ сервера (ожидался JSON)"}

            return response.json()

        except requests.RequestException as e:
            print(f"💥 Критическая ошибка сети при запросе списка инбаундов: {e}")
            return {"success": False, "msg": str(e)}
        except ValueError as e:
            print(f"💥 Ошибка парсинга JSON со списком инбаундов: {e}")
            return {"success": False, "msg": "Ошибка декодирования JSON"}

    def get_inbound_id_by_remark(self, remark: str) -> int | None:
        """
        Ищет ID инбаунда по его названию (remark).
        Возвращает int ID или None, если инбаунд не найден.
        """
        data = self.users()

        # Проверяем корректность ответа структуры API
        if not data or not data.get("success"):
            print(f"⚠️ Не удалось получить список инбаундов для поиска remark '{remark}'")
            return None

        # Поиск совпадения по remark
        for inbound in data.get("obj", []):
            if inbound.get("remark") == remark:
                return inbound.get("id")

        print(f"🔍 Инбаунд с названием '{remark}' не найден.")
        return None





if __name__ == "__main__":
    api = API()
    data = api.users()
    api.save_json_data(data, "users.json")