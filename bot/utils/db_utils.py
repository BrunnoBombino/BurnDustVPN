from sqlalchemy import select, or_
from core.database import User, async_session
from sqlalchemy import update


async def bind_tg_to_user(tg_id: int, token: str) -> bool:
    async with async_session() as session:
        # 1. Ищем пользователя с таким токеном
        result = await session.execute(select(User).where(User.activation_token == token))
        user = result.scalar_one_or_none()

        if not user:
            return False

        # 2. Привязываем ТГ ID и затираем токен (чтобы он был одноразовым)
        user.telegram_id = tg_id
        user.activation_token = None

        await session.commit()
        return True


async def get_user_by_tg_id(tg_id: int):
    """Возвращает пользователя из БД или None"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        return result.scalar_one_or_none()

async def check_user_exists(login=None, email=None):
    async with async_session() as session:
        query = select(User).where(or_(User.username == login, User.email == email))
        result = await session.execute(query)
        return result.scalar_one_or_none() is not None

