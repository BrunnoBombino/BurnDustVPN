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
    def __init__(self, cookie_file="session_cookies.pkl") -> None:
        # Инициализируем объект сессии requests
        self.ses = requests.Session()

        # Определяем корень проекта (поднимаемся на 1 уровень вверх из папки core)
        self.base_dir = Path(__file__).resolve().parent.parent
        # Делаем путь к файлу бэкапа абсолютным относительно корня проекта
        self.backup_path = self.base_dir / "backup_lost_users.txt"

        self.host = auth.HOST
        self.API_TOKEN = auth.API_TOKEN


    def connect(self) -> bool:
        if hasattr(auth, 'API_TOKEN') and self.API_TOKEN:
            self.ses.headers.update({"Authorization": f"Bearer {self.API_TOKEN}"})
            return True
        return False

    @staticmethod
    def save_json_data(data, file_name):
        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def users(self):
        """Получает список инбаундов с использованием API токена."""
        # Настраиваем заголовки сессии (подтягиваем токен)
        if not self.connect():
            return {"success": False, "msg": "API токен не настроен в auth.py"}

        try:
            # Делаем GET-запрос. Токен уже находится в self.ses.headers благодаря методу connect()
            response = self.ses.get(f"{self.host}/panel/api/inbounds/list", timeout=10, verify=False)

            # Проверяем HTTP статус-код ответа
            if response.status_code == 401 or response.status_code == 403:
                print("❌ Ошибка: Панель отклонила API токен. Проверьте правильность токена в auth.py.")
                return {"success": False, "msg": f"Ошибка авторизации токена (Статус {response.status_code})"}

            if response.status_code != 200:
                print(f"❌ Непредвиденная ошибка сервера. Статус-код: {response.status_code}")
                return {"success": False, "msg": f"Ошибка HTTP {response.status_code}"}

            # Проверяем, что ответ не пустой и содержит JSON
            if not response.text.strip() or "html" in response.headers.get("Content-Type", "").lower():
                print("❌ Ошибка: Сервер вернул некорректный ответ (пустой или HTML) вместо списка пользователей.")
                return {"success": False, "msg": "Невалидный ответ сервера"}

            # Безопасно парсим и возвращаем JSON результат
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
        Возвращает ID (int) в случае успеха или None, если инбаунд не найден.
        """
        data = self.users()

        if not data or not data.get("success"):
            print(f"⚠️ Не удалось получить список инбаундов для поиска remark '{remark}'")
            return None

        # Обходим список всех инбаундов в ключе 'obj'
        for inbound in data.get("obj", []):
            if inbound.get("remark") == remark:
                return inbound.get("id")

        print(f"🔍 Инбаунд с названием '{remark}' не найден.")
        return None





if __name__ == "__main__":
    api = API()
    data = api.users()
    api.save_json_data(data, "users.json")