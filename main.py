from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from core.database import init_db, get_db
from core.services import create_new_user_vpn_key
import core.services as services

app = FastAPI(title="VPN Service API")

# При старте приложения создаем таблицы, если их еще нет
@app.on_event("startup")
def on_startup():
    init_db()
    print("✅ База данных успешно инициализирована")

@app.get("/api/vpn/my-keys")
def get_my_keys(user_id: int, db: Session = Depends(get_db)):
    # Метод моментально отдаст массив строк из базы, не нагружая сеть
    links = services.get_user_vless_links(db, user_id=user_id)
    return {"success": True, "links": links}

# Тестовый эндпоинт для проверки генерации ключа
@app.post("/api/vpn/test-create-key")
def test_create_key(user_id: int, db: Session = Depends(get_db)):
    result = create_new_user_vpn_key(db, user_id=user_id)
    return result