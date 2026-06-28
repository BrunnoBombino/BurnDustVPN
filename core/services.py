import base64
import string
import urllib
import uuid
import secrets
import bcrypt
import jwt
from sqlalchemy.orm import Session
from core.database import Node, Connection
from datetime import datetime, timezone, timedelta
from core.database import User
from core.xuiclient import XUIClient
from core.endpoints import XUINodeEndpoints, XUIClientsEndpoints, XUIInboundEndpoints
from core.config import VPNConfig, settings


def get_xui_client(node: Node) -> XUIClient:
    """Фабрика для создания клиентов к конкретной ноде"""
    return XUIClient(host=node.xui_host, token=node.xui_token)

def create_new_user_vpn_key(db: Session, user_id: int) -> dict:
    # 1. Поиск ноды (как было)
    best_node = db.query(Node).filter(Node.is_active == True).order_by(Node.cpu_load.asc()).first()
    if not best_node:
        return {"success": False, "msg": "Нет доступных нод"}

    client_uuid = str(uuid.uuid4())
    client_email = f"user_{user_id}_{secrets.token_hex(4)}"
    # Генерируем sub_id заранее, чтобы сохранить в БД сразу
    client_sub_id = generate_sub_id()

    node_client = XUIClient(host=best_node.xui_host, token=best_node.xui_token)
    inbound_ids = get_vless_reality_inbounds(node_client)

    if not inbound_ids:
        return {"success": False, "msg": "На ноде нет активных VLESS-Reality инбаундов"}

    # 2. Попытка создания на ноде
    res = node_client.add_client(
        client_email=client_email,
        client_uuid=client_uuid,
        inbound_ids=inbound_ids,
        subId=client_sub_id  # Передаем наш сгенерированный ID
    )

    if not res.get("success"):
        return {"success": False, "msg": "Ошибка API ноды"}

    # 3. Сохранение в БД с уже имеющимся sub_id
    try:
        new_conn = Connection(
            user_id=user_id,
            node_id=best_node.id,
            client_uuid=client_uuid,
            client_email=client_email,
            sub_id=client_sub_id  # Сохраняем в таблицу
        )
        db.add(new_conn)
        db.commit()
    except Exception as e:
        db.rollback()
        node_client.delete_client(client_email)
        return {"success": False, "msg": f"Database error: {str(e)}"}

    # 4. Формируем ссылку для пользователя
    # Теперь мы даже не опрашиваем API, мы берем данные из только что созданного объекта
    link = f"http://{best_node.public_ip}:{VPNConfig.SUB_PORT}/sub/{client_sub_id}"

    return {"success": True, "link": link}

def delete_user_vpn_key(db: Session, connection_id: int) -> dict:
    conn = db.query(Connection).filter(Connection.id == connection_id).first()
    if not conn:
        return {"success": False, "msg": "Соединение не найдено"}

    node = conn.node
    node_client = XUIClient(host=node.xui_host, token=node.xui_token)

    base_endpoint = XUIClientsEndpoints.DELETE_CLIENT.rstrip('/')
    endpoint = f"{base_endpoint}/{conn.client_email}"

    response = node_client._make_request("POST", endpoint)

    if response.get("success"):
        db.delete(conn)
        db.commit()
        return {"success": True}

    return {"success": False, "msg": f"Ошибка удаления: {response.get('msg', 'Unknown error')}"}

def generate_vless_link(node: Node, client_uuid: str, client_email: str) -> str:
    """Вспомогательная функция сборки ссылки на основе модели Ноды"""
    return (
        f"vless://{client_uuid}@{node.public_ip}:{node.vless_port}"
        f"?encryption=none&flow=xtls-rprx-vision&security=reality"
        f"&sni={node.sni}&fp=chrome&pbk={node.public_key}&sid={node.short_id}"
        f"#{node.name}-{client_email}"
    )

def generate_sub_id():
    # Генерируем случайную строку из 16 строчных латинских букв и цифр
    alphabet = string.ascii_lowercase + string.digits
    client_sub_id = "".join(secrets.choice(alphabet) for _ in range(16))
    return client_sub_id

def get_user_subscription_link(db: Session, user_id: int) -> list:
    """
    Возвращает список URL подписок для всех активных подключений пользователя.
    """
    connections = db.query(Connection).filter(
        Connection.user_id == user_id,
        Connection.is_enabled == True
    ).all()

    links = []
    for conn in connections:
        # Теперь мы просто формируем URL с sub_id, который ты сохранил при создании
        node = conn.node
        link = f"http://{node.public_ip}:{VPNConfig.SUB_PORT}/sub/{conn.sub_id}"
        links.append(link)

    return links

def get_vless_reality_inbounds(node_client: XUIClient) -> list:
    """Опрашивает ноду и возвращает список всех VLESS-Reality ID."""
    endpoint = XUIInboundEndpoints.INBOUNDS_LIST
    response = node_client._make_request("GET", endpoint)
    inbounds = response.get("obj", [])

    target_ids = []
    for inbound in inbounds:
        # Проверяем протокол и security
        # В структуре 3x-ui streamSettings -> security
        stream_settings = inbound.get("streamSettings", {})
        if inbound.get("protocol") == "vless" and stream_settings.get("security") == "reality":
            target_ids.append(inbound["id"])

    return target_ids

def update_nodes_from_master(db, xui_master):
    response = xui_master._make_request("GET", "/panel/api/nodes/list")
    nodes_data = response.get("obj", [])

    for node_info in nodes_data:
        # 1. Формируем чистый хост, удаляя лишние слэши
        # basePath в 3x-ui обычно начинается и заканчивается слэшем,
        # например "/Nh9O0nGM3Q43qHXg5N/"
        base_path = node_info.get("basePath", "").strip("/")
        base_path = f"/{base_path}/" if base_path else "/"

        full_host = f"{node_info['scheme']}://{node_info['address']}:{node_info['port']}{base_path}".rstrip('/')

        # 2. Проверяем наличие ноды
        existing_node = db.query(Node).filter(Node.guid == node_info["guid"]).first()

        if not existing_node:
            new_node = Node(
                guid=node_info["guid"],
                name=node_info["name"],
                xui_host=full_host,
                xui_token=node_info["apiToken"],
                public_ip=node_info["address"],
                vless_port=node_info["port"],
                is_active=node_info["enable"],
                # Заполняем поля заглушками, чтобы не было ошибки NOT NULL
                public_key="",
                short_id="",
                sni="google.com"
            )
            db.add(new_node)
            print(f"✅ Добавлена новая нода: {new_node.name} (Host: {full_host})")
        else:
            # Обновляем данные, если они могли измениться
            existing_node.xui_host = full_host
            existing_node.xui_token = node_info["apiToken"]
            existing_node.cpu_load = node_info["cpuPct"]
            existing_node.mem_load = node_info["memPct"]
            existing_node.is_active = node_info["enable"]

    db.commit()

def hash_password(password: str) -> str:
    """Превращает пароль в безопасный хэш"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, подходит ли пароль к хэшу"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_user(db: Session, email: str, password: str) -> User | None:
    """Создает нового пользователя, если email свободен"""
    # Проверяем, нет ли уже такого email в БД
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return None

    new_user = User(
        email=email,
        password_hash=hash_password(password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=30)) -> str:
    """Создает JWT токен для авторизации на сайте/в боте"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
