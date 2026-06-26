from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import random  # Для примера, ниже заменим на логику

app = FastAPI(title="VPN Management API")

# Эмуляция базы данных нод (в будущем тут будет PostgreSQL)
NODES_DB = [
    {"id": 1, "host": "http://node1.test:2053", "token": "tok1", "current_load": 45},
    {"id": 2, "host": "http://node2.test:2053", "token": "tok2", "current_load": 12},  # Самая свободная
    {"id": 3, "host": "http://node3.test:2053", "token": "tok3", "current_load": 88},
]


# Схема данных, которую мы ожидаем от фронтенда или бота при регистрации
class UserRegister(BaseModel):
    email: str
    password: str


@app.post("/api/auth/register")
def register_user(user: UserRegister):
    # Тут будет логика записи в БД PostgreSQL
    return {"status": "success", "message": f"Пользователь {user.email} зарегистрирован"}


@app.post("/api/connections/create")
def create_connection(user_id: int):
    """Алгоритм выбора наименее загруженной ноды и создания ключа"""

    # 1. Выбираем самую свободную ноду из активных
    # Сортируем список по ключу current_load от меньшего к большему
    sorted_nodes = sorted(NODES_DB, key=lambda x: x["current_load"])
    best_node = sorted_nodes[0]

    # 2. Здесь мы бы вызвали твой класс XUIClient для отправки запроса на эту ноду
    # client = XUIClient(host=best_node["host"], token=best_node["token"])
    # response = client.add_client_to_xui(...)

    return {
        "success": True,
        "selected_node": best_node["host"],
        "config": f"vless://fake-uuid-generated-for-user-{user_id}@{best_node['host']}?type=tcp"
    }

# Запуск сервера (в терминале: uvicorn main:app --reload)