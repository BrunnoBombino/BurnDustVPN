from sqlalchemy import select
from core.database import async_session, User

async def get_user_by_tg_id(tg_id: int):
    """Возвращает пользователя из БД или None"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        return result.scalar_one_or_none()