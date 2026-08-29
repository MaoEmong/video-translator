from fastapi import Depends

from app.config import Settings, get_settings
from app.storage.s3 import S3Storage


def get_storage(settings: Settings = Depends(get_settings)) -> S3Storage:
    return S3Storage(settings)
