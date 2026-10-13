from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class StorageBackend(ABC):
    """
    Interface de stockage de fichiers. L'implémentation locale (disque) est
    utilisée aujourd'hui ; passer à un stockage cloud (S3, Cloudinary,
    Supabase Storage...) plus tard ne demandera qu'une nouvelle classe
    implémentant cette même interface, sans toucher au reste de l'application.
    """

    @abstractmethod
    def save(self, file_obj: BinaryIO, stored_filename: str) -> int:
        """Écrit le contenu et retourne la taille en octets."""

    @abstractmethod
    def open(self, stored_filename: str) -> BinaryIO:
        """Ouvre le fichier en lecture binaire."""

    @abstractmethod
    def delete(self, stored_filename: str) -> None:
        ...

    @abstractmethod
    def path_for(self, stored_filename: str) -> Path:
        """Ne doit être utilisé qu'en interne (jamais exposé tel quel au client)."""
