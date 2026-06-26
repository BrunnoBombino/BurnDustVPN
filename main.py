from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from core.database import init_db, get_db
from core.services import create_new_user_vpn_key

app = FastAPI(title="VPN Service API")

# При старте приложения создаем таблицы, если их еще нет
@app.on_event("startup")
def on_startup():
    init_db()
    print("✅ База данных успешно инициализирована")

@app.get("/")
def read_root():
    return {"message": "Бэкенд VPN сервиса запущен!"}

# Тестовый эндпоинт для проверки генерации ключа
@app.post("/api/vpn/test-create-key")
def test_create_key(user_id: int, db: Session = Depends(get_db)):
    result = create_new_user_vpn_key(db, user_id=user_id)
    return result