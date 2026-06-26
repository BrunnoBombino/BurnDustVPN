import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


# 1. Таблица ПОЛЬЗОВАТЕЛЕЙ
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # Поле для интеграции с Telegram. По умолчанию None.
    # Когда пользователь привяжет бота, сюда запишется его ТГ ID.
    telegram_id = Column(Integer, unique=True, nullable=True, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Связь с таблицей подключений (у одного юзера может быть много ключей)
    connections = relationship("Connection", back_populates="user")


# 2. Таблица СЕРВЕРОВ (НОД)
class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Красивое название, например "Германия 1"
    xui_host = Column(String, nullable=False)  # URL панели для API, например "http://1.2.3.4:2053"
    xui_token = Column(String, nullable=False)  # Bearer токен для API этой ноды

    # Параметры для сборки vless:// ссылки (чтобы не запрашивать их из панели)
    public_ip = Column(String, nullable=False)  # IP для подключения клиентов
    vless_port = Column(Integer, nullable=False)  # Порт инбаунда
    public_key = Column(String, nullable=False)  # Reality Public Key
    short_id = Column(String, nullable=False)  # Reality Short ID
    sni = Column(String, default="google.com")  # Reality SNI (маскировка)
    inbound_id = Column(Integer, nullable=False)  # ID инбаунда внутри 3x-ui

    # Метрики для балансировки нагрузки
    current_load = Column(Float, default=0.0)  # Текущая загрузка в % или кол-во активных юзеров
    is_active = Column(Boolean, default=True)  # Включен ли сервер в систему распределения

    connections = relationship("Connection", back_populates="node")


# 3. Таблица ПОДКЛЮЧЕНИЙ (Ключей пользователей)
class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)

    # Уникальный UUID клиента, который прописывается в 3x-ui и вставляется в ссылку
    client_uuid = Column(String, unique=True, default=lambda: str(uuid.uuid4()), nullable=False)
    # Email клиента внутри панели (например: user_12_key_1)
    client_email = Column(String, nullable=False)

    is_enabled = Column(Boolean, default=True)  # Активен ли ключ (оплачен/заблокирован)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Отношения (relationships) для удобного доступа к объектам в коде
    user = relationship("User", back_populates="connections")
    node = relationship("Node", back_populates="connections")