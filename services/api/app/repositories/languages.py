from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language import Language


class LanguageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_enabled(self) -> list[Language]:
        result = await self.session.scalars(select(Language).order_by(Language.code))
        return list(result)
