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

    def generate_vless_link(self, inbound_id: int, client_uuid: str, client_email: str) -> str | None:
        """
        Автоматически собирает vless:// ссылку для Reality
        """
        inbound_data = self.get_inbound_status(inbound_id)
        if not inbound_data or not inbound_data.get("success"):
            print("❌ Не удалось получить данные инбаунда для сборки ссылки")
            return None

        obj = inbound_data.get("obj", {})
        port = obj.get("port")
        remark = obj.get("remark", "VPN")

        # Десериализуем streamSettings, так как 3x-ui хранит их строкой внутри JSON
        stream_settings = json.loads(obj.get("streamSettings", "{}"))

        # Вытаскиваем параметры Reality
        reality_settings = stream_settings.get("realitySettings", {})
        server_names = reality_settings.get("serverNames", ["google.com"])
        sni = server_names[0] if server_names else "google.com"

        # Публичный ключ и shortId лежат внутри приватных настроек инбаунда
        settings = json.loads(obj.get("settings", "{}"))
        # Нам нужен publicKey, его можно забрать из базы или передавать константой,
        # но в последних версиях 3x-ui его можно выудить из streamSettings
        ext_settings = stream_settings.get("externalProxy", [])  # или из полей панели

        # ВАЖНО: Так как publicKey генерируется при создании инбаунда,
        # проще всего один раз сохранить его настройки в твою БД нод.
        # Но если мы берем напрямую из панели (для Reality):
        private_key_list = reality_settings.get("shortIds", [""])
        short_id = private_key_list[0] if private_key_list else ""
        pub_key = reality_settings.get("settings", {}).get("publicKey", "")

        # Если панель не отдала pub_key через этот эндпоинт (зависит от версии),
        # то надежнее передавать параметры сети ноды из твоей БД.
        # Шаблон VLESS Reality строки:
        # vless://UUID@IP:PORT?encryption=none&flow=xtls-rprx-vision&security=reality&sni=SNI&fp=chrome&pbk=PUBLIC_KEY&sid=SHORT_ID#REMARK

        # Для примера, вот сборка строки:
        link = f"vless://{client_uuid}@{self.public_ip}:{port}?encryption=none&flow=xtls-rprx-vision&security=reality&sni={sni}&fp=chrome&pbk={pub_key}&sid={short_id}#{remark}-{client_email}"
        return link

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


