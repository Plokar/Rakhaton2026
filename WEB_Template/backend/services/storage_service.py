"""
Storage Service – File Storage Abstraction for Hackathons
Supports: Local Disk Storage and S3 / MinIO compatible storage.
"""
import os
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class StorageProvider(ABC):
    """Abstraktní rozhraní pro správu souborů"""

    @abstractmethod
    def upload(self, file_obj, folder: str = "uploads") -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete(self, file_path: str) -> bool:
        pass

    @abstractmethod
    def get_url(self, file_path: str) -> str:
        pass


class LocalStorageProvider(StorageProvider):
    """Lokální diskové úložiště (výchozí pro hackathony)"""

    def __init__(self):
        self.media_root = settings.MEDIA_ROOT
        self.media_url = settings.MEDIA_URL
        os.makedirs(self.media_root, exist_ok=True)

    def upload(self, file_obj, folder: str = "uploads") -> Dict[str, Any]:
        target_dir = os.path.join(self.media_root, folder)
        os.makedirs(target_dir, exist_ok=True)

        original_name = getattr(file_obj, 'name', 'unnamed')
        ext = os.path.splitext(original_name)[1]
        unique_filename = f"{uuid.uuid4().hex[:12]}_{original_name}"
        full_path = os.path.join(target_dir, unique_filename)

        size = 0
        with open(full_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
                size += len(chunk)

        relative_path = os.path.join(folder, unique_filename).replace('\\', '/')
        url = f"{self.media_url.rstrip('/')}/{relative_path.lstrip('/')}"

        return {
            "filename": unique_filename,
            "original_name": original_name,
            "path": full_path,
            "relative_path": relative_path,
            "url": url,
            "size": size,
            "mime_type": getattr(file_obj, 'content_type', 'application/octet-stream')
        }

    def delete(self, file_path: str) -> bool:
        try:
            full_path = file_path if os.path.isabs(file_path) else os.path.join(self.media_root, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
        return False

    def get_url(self, file_path: str) -> str:
        relative = file_path.replace(str(self.media_root), '').lstrip('/\\').replace('\\', '/')
        return f"{self.media_url.rstrip('/')}/{relative}"


def get_storage() -> StorageProvider:
    """Vrátí instanci aktivního storage providera"""
    # Lze snadno rozšířit o S3/MinIO v budoucnu
    return LocalStorageProvider()
