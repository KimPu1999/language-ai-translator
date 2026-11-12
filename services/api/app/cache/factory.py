from app.cache.base import TranslationCache
from app.cache.null import NullTranslationCache
from app.cache.redis import RedisTranslationCache
from app.core.config import get_settings


def get_translation_cache() -> TranslationCache:
    settings = get_settings()
    if not settings.translation_cache_enabled:
        return NullTranslationCache()
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL is required when translation caching is enabled")
    return RedisTranslationCache(settings.redis_url)
