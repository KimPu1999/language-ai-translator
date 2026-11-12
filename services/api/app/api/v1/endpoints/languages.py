from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.providers.translation.registry import TranslationProviderRegistry, get_translation_registry
from app.repositories.languages import LanguageRepository
from app.schemas.language import LanguageResponse

router = APIRouter(prefix="/api/v1", tags=["languages"])


@router.get("/languages", response_model=list[LanguageResponse])
async def languages(db: AsyncSession = Depends(get_db)) -> list[LanguageResponse]:
    return await LanguageRepository(db).list_enabled()


@router.get("/capabilities")
async def capabilities(
    registry: TranslationProviderRegistry = Depends(get_translation_registry),
) -> dict[str, object]:
    return {
        "text_translation": "text_translation" in registry.supported_operations,
        "language_detection": "language_detection" in registry.supported_operations,
        "provider_configured": registry.configured,
        "provider": "azure" if registry.configured else None,
        "supported_operations": sorted(registry.supported_operations),
    }
