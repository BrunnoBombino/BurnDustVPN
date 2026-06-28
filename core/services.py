import uuid
import secrets
from sqlalchemy.orm import Session
from core.database import Node, Connection
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from core.database import User
from core.xuiclient import XUIClient
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()

SECRET_KEY = "SUPER_SECRET_KEY_CHANGE_ME" # В будущем вынесем в auth.py
ALGORITHM = "HS256"


def get_xui_client_for_node(node: Node) -> XUIClient:
    return XUIClient(host=node.xui_host, token=node.xui_token)

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
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)