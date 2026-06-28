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
    guid = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    xui_host = Column(String, nullable=False)
    xui_token = Column(String, nullable=False)
    public_ip = Column(String, nullable=True, default="")
    vless_port = Column(Integer, nullable=False)
    public_key = Column(String, nullable=True, server_default="")
    short_id = Column(String, nullable=True, default="")
    sni = Column(String, nullable=True, default="google.com")
    inbound_id = Column(Integer, nullable=True, default=0)

    # Метрики
    is_active = Column(Boolean, default=True)
    cpu_load = Column(Float, default=0.0)
    mem_load = Column(Float, default=0.0)
    latency = Column(Integer, default=0)

    connections = relationship("Connection", back_populates="node")

class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
    inbound_id = Column(Integer)

    client_uuid = Column(String, unique=True, default=lambda: str(uuid.uuid4()), nullable=False)
    client_email = Column(String, nullable=False)

    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="connections")
    node = relationship("Node", back_populates="connections")


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