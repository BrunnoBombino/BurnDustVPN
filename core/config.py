import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# Получаем путь к папке, где лежит config.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str

    # Явно указываем путь к .env в корне проекта
    model_config = SettingsConfigDict(env_file=os.path.join(BASE_DIR, ".env"))


settings = Settings()

class VPNConfig:
    DEFAULT_FLOW = "xtls-rprx-vision"
    DEFAULT_LIMIT_IP = 1
    DEFAULT_EXPIRY_TIME = 0
    DEFAULT_TOTAL_GB = 0
    SUB_PORT = 2096  # Порт для ссылок подписки