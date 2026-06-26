import json
from requests import RequestException, Session
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class XUIClient:
    def __init__(self, host: str, token: str) -> None:
        self.ses = Session()
        self.host = host.rstrip('/')
        # 3x-ui принимает авторизацию через Bearer токен в заголовок
        self.ses.headers.update({"Authorization": f"Bearer {token}"})

    def _make_request(self, method: str, endpoint: str, json_data: dict = None) -> dict:
        """Внутренний вспомогательный метод для отправки запросов (DRY)"""
        url = f"{self.host}{endpoint}"
        try:
            response = self.ses.request(method, url, json=json_data, timeout=10, verify=False)

            if response.status_code in (401, 403):
                return {"success": False, "msg": "Ошибка авторизации в панели 3x-ui"}

            if response.status_code != 200:
                return {"success": False, "msg": f"Ошибка HTTP {response.status_code}"}

            return response.json()
        except RequestException as e:
            return {"success": False, "msg": f"Ошибка сети: {e}"}

    def get_inbounds(self) -> dict:
        """Получить список всех инбаундов (протоколов/портов) на этой ноде"""
        return self._make_request("GET", "/panel/api/inbounds/list")

    def add_client(self, inbound_id: int, client_email: str, client_uuid: str, limit_gb: int = 0,
                   expiry_days: int = 0) -> dict:
        """
        Добавляет нового пользователя (клиента) в существующий инбаунд.
        :param inbound_id: ID инбаунда (например, твой VLESS под номером 1)
        :param client_email: Уникальный email/логин внутри этого инбаунда (для идентификации)
        :param client_uuid: Сгенерированный тобой UUID (строка)
        :param limit_gb: Лимит трафика в Гигабайтах (0 — безлимит)
        :param expiry_days: Через сколько дней отключить (0 — вечно)
        """
        # Переводим ГБ в байты (3x-ui считает в байтах)
        total_gb_bytes = limit_gb * 1024 * 1024 * 1024 if limit_gb > 0 else 0

        # Переводим дни в таймстамп миллисекунд (отрицательное значение в 3x-ui означает срок окончания)
        # Если нужно задать точную дату, она передается как отрицательный timestamp в мс.
        # Для простоты пока оставим 0 (без лимита по времени), сроки лучше контролировать на стороне нашей БД.

        payload = {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [
                    {
                        "id": client_uuid,
                        "alterId": 0,
                        "email": client_email,
                        "limitIp": 2,  # Ограничение на 2 одновременных IP (на всякий случай)
                        "totalGB": total_gb_bytes,
                        "expiryTime": 0,
                        "enable": True,
                        "flow": "xtls-rprx-vision"  # Оставь пустым "", если используешь не VLESS-Reality
                    }
                ]
            })
        }

        return self._make_request("POST", "/panel/api/inbounds/addClient", json_data=payload)

    def delete_client(self, inbound_id: int, client_uuid: str) -> dict:
        """
        Удаляет клиента из инбаунда по его UUID.
        """
        endpoint = f"/panel/api/inbounds/Client/{client_uuid}"  # В некоторых версиях 3x-ui удаление идет через UUID
        # Если в твоей версии удаление идет по email, эндпоинт будет /panel/api/inbounds/{inbound_id}/delClient/{client_email}
        # Но актуальный 3x-ui принимает POST запрос на /panel/api/inbounds/delClient/{client_uuid}

        return self._make_request("POST", f"/panel/api/inbounds/delClient/{client_uuid}")

    def toggle_client(self, inbound_id: int, client_uuid: str, enable: bool) -> dict:
        """
        Включает или выключает (блокирует) клиента, не удаляя его настройки.
        Удобно для блокировки за неуплату.
        """
        payload = {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [
                    {
                        "id": client_uuid,
                        "enable": enable
                    }
                ]
            })
        }
        # В 3x-ui обновление клиента происходит через updateClient
        return self._make_request("POST", f"/panel/api/inbounds/updateClient/{client_uuid}", json_data=payload)

    def get_client_traffic(self, client_email: str) -> dict:
        """
        Получить статистику трафика конкретного клиента по его email.
        Возвращает скачано/загружено.
        """
        # Эндпоинт для получения статы одиночного клиента
        return self._make_request("POST", f"/panel/api/inbounds/getClientTraffics/{client_email}")






    # def users(self) -> dict:
    #     """Получает список инбаундов."""
    #     try:
    #         # Больше не нужно вызывать connect(), хедер уже в сессии
    #         url = f"{self.host}/panel/api/inbounds/list"
    #         response = self.ses.get(url, timeout=10, verify=False)
    #
    #         if response.status_code in (401, 403):
    #             return {"success": False, "msg": "Ошибка авторизации (Токен неверный)"}
    #
    #         if response.status_code != 200:
    #             return {"success": False, "msg": f"Ошибка HTTP {response.status_code}"}
    #
    #         return response.json()
    #     except requests.RequestException as e:
    #         return {"success": False, "msg": f"Ошибка сети: {e}"}


