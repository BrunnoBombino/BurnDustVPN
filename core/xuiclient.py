import json
import urllib3

from pathlib import Path
from requests import RequestException, Session

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

    def add_client(self, inbound_id: int, client_email: str, client_uuid: str, limit_gb: int = 0,
                   expiry_days: int = 0) -> dict:
        """
        Добавляет нового пользователя (клиента) в панель 3x-ui.
        """
        # Переводим ГБ в байты
        total_gb_bytes = limit_gb * 1024 * 1024 * 1024 if limit_gb > 0 else 0

        # Строгое соответствие ожидаемой структуре панели
        payload = {
            "client": {
                "id": client_uuid,  # Уникальный UUID для подключения
                "email": client_email,  # Имя клиента в панели
                "totalGB": total_gb_bytes,
                "expiryTime": 0,  # 0 - без лимита по времени
                "tgId": 0,  # Integer
                "limitIp": 0,
                "enable": True,
                "flow": "xtls-rprx-vision"  # Обязательно для VLESS-Reality
            },
            "inboundIds": [
                inbound_id
            ]
        }

        return self._make_request("POST", "/panel/api/clients/add", json_data=payload)

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


