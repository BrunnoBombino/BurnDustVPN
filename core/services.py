# services.py
import uuid
import secrets
from sqlalchemy.orm import Session

# Теперь импортируем с указанием папки core
from core.database import Node, Connection
from core.xuiclient import XUIClient


def generate_vless_link(node: Node, client_uuid: str, client_email: str) -> str:
    """Вспомогательная функция сборки ссылки"""
    return (
        f"vless://{client_uuid}@{node.public_ip}:{node.vless_port}"
        f"?encryption=none&flow=xtls-rprx-vision&security=reality"
        f"&sni={node.sni}&fp=chrome&pbk={node.public_key}&sid={node.short_id}"
        f"#{node.name}-{client_email}"
    )


def create_new_user_vpn_key(db: Session, user_id: int) -> dict:
    """Основная логика создания VPN подключения"""

    # 1. Находим самую незагруженную ноду (исправил опечатку: order_by вместо order_style)
    best_node = db.query(Node).filter(Node.is_active == True).order_by(Node.current_load.asc()).first()

    if not best_node:
        return {"success": False, "msg": "Нет доступных серверов"}

    # 2. Генерируем уникальные данные для ключа
    client_uuid = str(uuid.uuid4())
    client_email = f"user_{user_id}_{secrets.token_hex(3)}"

    # 3. Стучимся в панель 3x-ui на выбранной ноде
    xui = XUIClient(host=best_node.xui_host, token=best_node.xui_token)
    xui_response = xui.add_client(
        inbound_id=best_node.inbound_id,
        client_email=client_email,
        client_uuid=client_uuid
    )

    if not xui_response.get("success"):
        return {"success": False, "msg": f"Ошибка 3x-ui: {xui_response.get('msg')}"}

    # 4. Сохраняем в нашу БД
    new_conn = Connection(
        user_id=user_id,
        node_id=best_node.id,
        client_uuid=client_uuid,
        client_email=client_email
    )
    db.add(new_conn)

    # 5. Имитируем рост нагрузки (+1 активное подключение)
    best_node.current_load += 1
    db.commit()

    # 6. Генерируем ссылку
    vpn_link = generate_vless_link(best_node, client_uuid, client_email)

    return {"success": True, "link": vpn_link}