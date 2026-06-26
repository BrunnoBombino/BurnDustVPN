# core/services.py
import uuid
import secrets
from sqlalchemy.orm import Session
from core.database import Node, Connection


def generate_vless_link(node: Node, client_uuid: str, client_email: str) -> str:
    """Вспомогательная функция сборки ссылки на основе модели Ноды"""
    return (
        f"vless://{client_uuid}@{node.public_ip}:{node.vless_port}"
        f"?encryption=none&flow=xtls-rprx-vision&security=reality"
        f"&sni={node.sni}&fp=chrome&pbk={node.public_key}&sid={node.short_id}"
        f"#{node.name}-{client_email}"
    )


def update_nodes_from_master(db: Session, master_client) -> None:
    """
    Запрашивает у Мастер-панели актуальное состояние всех нод
    и обновляет их загруженность в нашей базе данных.
    """
    response = master_client._make_request("GET", "/panel/api/nodes/list")

    if not response or not response.get("success"):
        print("⚠️ Не удалось обновить данные нод с Мастер-сервера")
        return

    nodes_list = response.get("obj", [])

    for node_data in nodes_list:
        db_node = db.query(Node).filter(Node.inbound_id == node_data.get("id")).first()
        if db_node:
            connections_count = node_data.get("lastMinutesConnections", 0)
            db_node.current_load = float(connections_count)
            db_node.is_active = node_data.get("status", True)

    db.commit()


def create_new_user_vpn_key(db: Session, user_id: int, master_node_id: int = 1) -> dict:
    """
    Логика создания нового ключа: опрос мастера -> выбор свободной ноды -> создание в 3x-ui
    """
    from core.xuiclient import XUIClient  # Импорт внутри функции во избежание циклической зависимости

    master_node = db.query(Node).filter(Node.id == master_node_id).first()
    if not master_node:
        return {"success": False, "msg": "Мастер-сервер не найден в локальной БД"}

    xui_master = XUIClient(host=master_node.xui_host, token=master_node.xui_token)

    # Обновляем состояние нод прямо перед выбором
    update_nodes_from_master(db, xui_master)

    # Выбираем самую свободную живую ноду
    best_node = db.query(Node).filter(Node.is_active == True).order_by(Node.current_load.asc()).first()
    if not best_node:
        return {"success": False, "msg": "Нет доступных серверов для подключения"}

    client_uuid = str(uuid.uuid4())
    client_email = f"user_{user_id}_{secrets.token_hex(3)}"

    # Добавляем клиента на Мастер (панель сама пробросит его на нужную ноду)
    xui_response = xui_master.add_client(
        inbound_id=best_node.inbound_id,
        client_email=client_email,
        client_uuid=client_uuid
    )

    if not xui_response.get("success"):
        return {"success": False, "msg": f"Ошибка 3x-ui: {xui_response.get('msg')}"}

    # Сохраняем в свою БД
    new_conn = Connection(
        user_id=user_id,
        node_id=best_node.id,
        client_uuid=client_uuid,
        client_email=client_email
    )
    db.add(new_conn)
    db.commit()

    vpn_link = generate_vless_link(best_node, client_uuid, client_email)
    return {"success": True, "link": vpn_link}


def get_user_vless_links(db: Session, user_id: int) -> list:
    """
    Возвращает список всех активных ссылок (конфигов) пользователя,
    просто собирая их из данных нашей БД (без запросов к 3x-ui).
    """
    connections = db.query(Connection).filter(
        Connection.user_id == user_id,
        Connection.is_enabled == True
    ).all()

    links = []
    for conn in connections:
        # Благодаря SQLAlchemy relationship, у conn есть свойство node
        node = conn.node
        if node:
            link = generate_vless_link(node, conn.client_uuid, conn.client_email)
            links.append(link)

    return links