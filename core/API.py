from pathlib import Path

import requests


class XUIClient:  # Переименуем для понятности, это клиент к 3x-ui
    def __init__(self, host: str, token: str) -> None:
        self.ses = requests.Session()
        self.host = host.rstrip('/')
        # Сразу задаем заголовок авторизации для этой сессии
        self.ses.headers.update({"Authorization": f"Bearer {token}"})

        self.base_dir = Path(__file__).resolve().parent.parent

    def users(self) -> dict:
        """Получает список инбаундов."""
        try:
            # Больше не нужно вызывать connect(), хедер уже в сессии
            url = f"{self.host}/panel/api/inbounds/list"
            response = self.ses.get(url, timeout=10, verify=False)

            if response.status_code in (401, 403):
                return {"success": False, "msg": "Ошибка авторизации (Токен неверный)"}

            if response.status_code != 200:
                return {"success": False, "msg": f"Ошибка HTTP {response.status_code}"}

            return response.json()
        except requests.RequestException as e:
            return {"success": False, "msg": f"Ошибка сети: {e}"}


