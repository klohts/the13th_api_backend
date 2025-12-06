import logging
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger("backend_v2.ingestion.config")


class IngestionSettings(BaseSettings):
    """Settings for ingestion (webhook + CSV).

    Environment variables (examples):

    INGESTION_API_KEYS="key1,key2,key3"
    INGESTION_MAX_CSV_SIZE_MB=5
    """

    ingestion_api_keys: List[str] = []
    max_csv_size_mb: int = 5

    class Config:
        env_prefix = "INGESTION_"
        env_file = ".env"
        extra = "ignore"

    @field_validator("ingestion_api_keys", mode="before")
    @classmethod
    def split_keys(cls, v):
        if not v:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return [item.strip() for item in str(v).split(",") if item.strip()]

    @field_validator("max_csv_size_mb", mode="before")
    @classmethod
    def validate_size(cls, v):
        val = int(v)
        if val <= 0:
            raise ValueError("INGESTION_MAX_CSV_SIZE_MB must be > 0")
        return val


@lru_cache(maxsize=1)
def get_ingestion_settings() -> IngestionSettings:
    settings = IngestionSettings()
    if not settings.ingestion_api_keys:
        logger.warning(
            "No ingestion API keys configured. Set INGESTION_API_KEYS to secure /ingestion endpoints."
        )
    logger.info(
        "IngestionSettings loaded (max_csv_size_mb=%s, keys=%d)",
        settings.max_csv_size_mb,
        len(settings.ingestion_api_keys),
    )
    return settings


ingestion_settings = get_ingestion_settings()
