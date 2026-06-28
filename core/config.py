from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()

class VPNConfig:
    DEFAULT_FLOW = "xtls-rprx-vision"
    DEFAULT_LIMIT_IP = 1
    DEFAULT_EXPIRY_TIME = 0
    DEFAULT_TOTAL_GB = 0
    SUB_PORT = 2096  # Порт для ссылок подписки