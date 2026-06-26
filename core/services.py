import uuid
import secrets
from sqlalchemy.orm import Session
from core.database import Node, Connection
from core.xuiclient import XUIClient


def update_nodes_from_master(db: Session, master_client: XUIClient):
    """
    Запрашивает у Мастер-панели актуальное состояние всех нод
    и обновляет их загруженность в нашей базе данных.
    """
    # Делаем запрос к мастер-панели для получения списка нод
    response = master_client._make_request("GET", "/panel/api/nodes/list")

    if not response or not response.get("success"):
        print("⚠️ Не удалось обновить данные нод с Мастер-сервера")
        return

    nodes_list = response.get("obj", [])

    for node_data in nodes_list:
        # Ищем ноду в нашей БД по xui_host или inbound_id
        # (в зависимости от того, как настроен 3x-ui, у каждой ноды есть свой ID в панели)
        db_node = db.query(Node).filter(Node.inbound_id == node_data.get("id")).first()

        if db_node:
            # Обновляем загрузку. В 3x-ui статус нагрузки можно взять из параметров ноды,
            # например, количество подключенных клиентов или использование CPU/RAM.
            # Для простоты возьмем гипотетическое поле 'connections' или статус 'lastMinutesConnections'
            connections_count = node_data.get("lastMinutesConnections", 0)

            db_node.current_load = float(connections_count)
            # Если нода не в сети (status false), выключаем её из балансировки
            db_node.is_active = node_data.get("status", True)

    db.commit()


def create_new_user_vpn_key(db: Session, user_id: int, master_node_id: int = 1) -> dict:
    """
    Бизнес-логика создания ключа: опрос мастера -> выбор ноды -> создание
    """
    # 1. Получаем данные самого Мастер-сервера из БД, чтобы авторизоваться в его API
    master_node = db.query(Node).filter(Node.id == master_node_id).first()
    if not master_node:
        return {"success": False, "msg": "Мастер-сервер не найден в локальной БД"}

    xui_master = XUIClient(host=master_node.xui_host, token=master_node.xui_token)

    # 2. Опрашиваем Мастер и обновляем загруженность всех остальных нод в нашей БД
    update_nodes_from_master(db, xui_master)

    # 3. Теперь выбираем из БД самую свободную и активную ноду
    best_node = db.query(Node).filter(Node.is_active == True).order_by(Node.current_load.asc()).first()

    if not best_node:
        return {"success": False, "msg": "Нет доступных серверов для подключения"}

    # 4. Генерируем уникальные данные для нового ключа пользователя
    client_uuid = str(uuid.uuid4())
    client_email = f"user_{user_id}_{secrets.token_hex(3)}"

    # 5. Создаем клиента. Запрос идет на Мастер-панель, но мы указываем inbound_id,
    # который привязан к выбранной ноде.
    xui_response = xui_master.add_client(
        inbound_id=best_node.inbound_id,
        client_email=client_email,
        client_uuid=client_uuid
    )

    if not xui_response.get("success"):
        return {"success": False, "msg": f"Ошибка 3x-ui при создании ключа: {xui_response.get('msg')}"}

    # 6. Сохраняем информацию о подключении в нашу БД
    new_conn = Connection(
        user_id=user_id,
        node_id=best_node.id,
        client_uuid=client_uuid,
        client_email=client_email
    )
    db.add(new_conn)
    db.commit()

    # 7. Конструируем ссылку vless:// на основе данных этой ноды из нашей БД
    vpn_link = (
        f"vless://{client_uuid}@{best_node.public_ip}:{best_node.vless_port}"
        f"?encryption=none&flow=xtls-rprx-vision&security=reality"
        f"&sni={best_node.sni}&fp=chrome&pbk={best_node.public_key}&sid={best_node.short_id}"
        f"#{best_node.name}"
    )

    return {"success": True, "link": vpn_link}