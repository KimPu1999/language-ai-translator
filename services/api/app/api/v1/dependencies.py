from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth import AuthContext, get_auth_context


async def current_auth_context(
    request: Request, db: AsyncSession = Depends(get_db)
) -> AuthContext:
    return await get_auth_context(request, db)
