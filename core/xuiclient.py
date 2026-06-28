import json
import urllib3

from pathlib import Path
from requests import RequestException, Session

from core.config import VPNConfig
from core.endpoints import XUIClientsEndpoints

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class XUIClient:
    def __init__(self, host: str, token: str, public_ip: str = None) -> None:
        self.ses = Session()
        self.host = host.rstrip('/')

        # Исправлено: если public_ip не передан, вырезаем его из хоста панели
        if public_ip:
            self.public_ip = public_ip
        else:
            # Например, из http://192.168.1.50:2053 достанет 192.168.1.50
            self.public_ip = self.host.split('://')[-1].split(':')[0]

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

    def get_inbound_by_id(self, inbound_id: int) -> dict:
        """
        Ищет инбаунд в списке по его ID.
        Возвращает словарь с настройками инбаунда или None, если не найден.
        """
        response = self.get_inbounds()  # Используем уже написанный метод

        if not response.get("success"):
            return None

        inbounds = response.get("obj", [])

        # Перебираем список и ищем совпадение
        for inbound in inbounds:
            if inbound.get("id") == inbound_id:
                return inbound

        return None

    def get_inbound_status(self, inbound_id: int) -> dict:
        """Получить настройки конкретного инбаунда (нужно для вытаскивания ключей Reality)"""
        res = self._make_request("GET", f"/panel/api/inbounds/get/{inbound_id}")
        return res

    @staticmethod
    def generate_vless_link(node: Node, client_uuid: str, client_email: str) -> str:
        """
        Моментально собирает vless ссылку на основе данных из нашей БД нод.
        """
        link = (
            f"vless://{client_uuid}@{node.public_ip}:{node.vless_port}"
            f"?encryption=none&flow=xtls-rprx-vision&security=reality"
            f"&sni={node.sni}&fp=chrome&pbk={node.public_key}&sid={node.short_id}"
            f"#{node.name}-{client_email}"
        )
        return link

    def find_client_by_email(self, email: str) -> dict:
        inbounds = self._make_request("GET", "/panel/api/inbounds/list")
        for inbound in inbounds.get("obj", []):
            for client in inbound.get("settings", {}).get("clients", []):
                if client.get("email") == email:
                    return {"inbound_id": inbound["id"], "client": client}
        return None

    def add_client(self, client_email: str, client_uuid: str,
                   limit_gb: int = VPNConfig.DEFAULT_TOTAL_GB,
                   expiry_time: int = VPNConfig.DEFAULT_EXPIRY_TIME, inbound_ids: list = None) -> dict:

        """
                Добавляет клиента глобально, привязывая его к списку inbound_ids.
                """
        # Если список ID не передан, попробуем добавить во все доступные VLESS-Reality
        if not inbound_ids:
            # Тут можно вызвать логику поиска, если нужно,
            # но лучше передавать готовый список из сервиса
            return {"success": False, "msg": "Список inbound_ids обязателен"}

        payload = {
            "client": {
                "id": client_uuid,
                "email": client_email,
                "enable": True,
                "totalGB": limit_gb * 1024 * 1024 * 1024 if limit_gb > 0 else 0,
                "expiryTime": expiry_time,
                "limitIp": 0,
                "flow": ""
            },
            "inboundIds": inbound_ids  # Вот тут вся магия "один клиент - много портов"
        }

        # Эндпоинт для глобального добавления клиента в 3x-ui
        return self._make_request("POST", "/panel/api/clients/add", json_data=payload)

        return self._make_request("POST", XUIClientsEndpoints.ADD_CLIENT, json_data=payload)

    def delete_client(self, inbound_id: int, email: str) -> dict:
        """
        Удаляет клиента из инбаунда по его UUID.
        """
        endpoint = f"{XUIClientsEndpoints.DELETE_CLIENT}/{email}"

        return self._make_request("POST", endpoint)

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
        Получает статистику трафика конкретного клиента по его email.
        """

        endpoint = f"/panel/api/clients/traffic/{client_email}"

        return self._make_request("GET", endpoint)

