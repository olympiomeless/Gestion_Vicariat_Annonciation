from functools import lru_cache

from app.core.config import settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend


@lru_cache
def get_storage_backend() -> StorageBackend:
    if settings.STORAGE_BACKEND == "local":
        return LocalStorageBackend(settings.STORAGE_LOCAL_PATH)
    # Point d'extension : "s3" / "cloudinary" / "supabase" pourraient être
    # ajoutés ici en implémentant StorageBackend, sans toucher au reste du code.
    raise ValueError(f"Backend de stockage inconnu : {settings.STORAGE_BACKEND}")
