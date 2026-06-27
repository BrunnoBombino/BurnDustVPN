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

    def add_client(self, inbound_id: int, client_email: str, client_uuid: str,
                   limit_gb: int = VPNConfig.DEFAULT_TOTAL_GB,
                   expiry_time: int = VPNConfig.DEFAULT_EXPIRY_TIME) -> dict:

        # 1. Получаем информацию об инбаунде для проверки протокола
        inbound = self.get_inbound_by_id(inbound_id)
        if not inbound:
            return {"success": False, "msg": f"Inbound {inbound_id} not found"}

        # 2. Определяем flow: используем дефолтный, если это VLESS
        protocol = inbound.get("protocol")
        flow = VPNConfig.DEFAULT_FLOW if protocol == "vless" else ""

        # 3. Конвертация лимита (ГБ -> Байты)
        total_gb_bytes = limit_gb * 1024 * 1024 * 1024 if limit_gb > 0 else 0

        # 4. Формируем тело запроса
        payload = {
            "client": {
                "id": client_uuid,
                "email": client_email,
                "enable": True,
                "totalGB": total_gb_bytes,
                "expiryTime": expiry_time,
                "tgId": 0,
                "limitIp": VPNConfig.DEFAULT_LIMIT_IP,
                "flow": flow
            },
            "inboundIds": [inbound_id]
        }

        return self._make_request("POST", XUIClientsEndpoints.ADD_CLIENT, json_data=payload)

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
        Получает статистику трафика конкретного клиента по его email.
        """

        endpoint = f"/panel/api/clients/traffic/{client_email}"

        return self._make_request("GET", endpoint)

