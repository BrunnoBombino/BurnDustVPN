# core/database.py
from datetime import datetime, timezone
import uuid
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# 1. Настройка подключения
# Для тестов используем SQLite (файл database_test.db создастся в корне)
DATABASE_URL = "sqlite:///./database_test.db"

# Аргумент check_same_thread нужен только для SQLite
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# 2. Определение моделей (Таблиц)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    telegram_id = Column(Integer, unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    connections = relationship("Connection", back_populates="user")


class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Например, "Германия 1"
    xui_host = Column(String, nullable=False)  # "http://1.2.3.4:2053"
    xui_token = Column(String, nullable=False)  # Токен панели

    # Данные для генерации ссылки
    public_ip = Column(String, nullable=False)
    vless_port = Column(Integer, nullable=False)
    public_key = Column(String, nullable=False)
    short_id = Column(String, nullable=False)
    sni = Column(String, default="google.com")
    inbound_id = Column(Integer, nullable=False)

    # Балансировка
    current_load = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)

    connections = relationship("Connection", back_populates="node")


class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)

    client_uuid = Column(String, unique=True, default=lambda: str(uuid.uuid4()), nullable=False)
    client_email = Column(String, nullable=False)

    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="connections")
    node = relationship("Node", back_populates="node")


# 3. Вспомогательная функция (Dependency) для FastAPI
def get_db():
    """Открывает сессию БД для каждого запроса и закрывает после его завершения"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Функция инициализации (создания) таблиц
def init_db():
    Base.metadata.create_all(bind=engine)