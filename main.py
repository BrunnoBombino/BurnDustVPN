from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status

from core.database import init_db, get_db
from core.services import create_user, verify_password, create_access_token, create_new_user_vpn_key
import core.database as db_models

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код до yield выполняется ПРИ СТАРТЕ приложения
    init_db()
    print("✅ База данных успешно инициализирована через lifespan")

    yield  # Здесь приложение работает

    # Код после yield выполнится ПРИ ВЫКЛЮЧЕНИИ приложения (если нужно)
    print("🛑 Приложение останавливается")



app = FastAPI(title="VPN Service API", lifespan=lifespan)

# Включаем CORS, чтобы фронтенд (веб-сайт) мог делать запросы к нашему API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажи конкретный домен сайта
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
def read_root():
    return {"message": "Бэкенд VPN сервиса работает отлично! Перейдите на /docs для просмотра API."}


# Схемы валидации входящих данных (Pydantic)
class UserAuthSchema(BaseModel):
    email: str  # Можно заменить на EmailStr, если установить pip install pydantic[email]
    password: str


# --- ЭНДПОИНТЫ АВТОРИЗАЦИИ ---

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(user_data: UserAuthSchema, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    user = create_user(db, email=user_data.email, password=user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже зарегистрирован"
        )
    return {"success": True, "message": "Вы успешно зарегистрировались!"}


@app.post("/api/auth/login")
def login(user_data: UserAuthSchema, db: Session = Depends(get_db)):
    """Вход в аккаунт (выдача токена)"""
    user = db.query(db_models.User).filter(db_models.User.email == user_data.email).first()

    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )

    # Генерируем токен, внутри зашиваем ID пользователя
    token = create_access_token(data={"user_id": user.id, "email": user.email})

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "telegram_id": user.telegram_id}
    }


# Временный тестовый эндпоинт для создания ключа (пока без проверки токена)
@app.post("/api/vpn/create-key")
def make_key(user_id: int, db: Session = Depends(get_db)):
    return create_new_user_vpn_key(db, user_id=user_id)