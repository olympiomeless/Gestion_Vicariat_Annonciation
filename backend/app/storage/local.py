import shutil
from pathlib import Path
from typing import BinaryIO

from app.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    """
    Stockage sur disque, EN DEHORS de toute racine servie statiquement par le
    serveur web : les fichiers ne sont accessibles que via l'endpoint API
    authentifié /documents/{id}/download, jamais par une URL directe
    (point 17 : "impossibilité d'accéder directement à un fichier privé en
    connaissant simplement son URL").
    """

    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, stored_filename: str) -> Path:
        # `stored_filename` est TOUJOURS généré côté serveur (voir
        # file_validation.generate_stored_filename) — jamais dérivé du nom
        # fourni par l'utilisateur. On revérifie quand même ici l'absence de
        # séparateurs de chemin, en défense en profondeur contre un appelant
        # qui passerait un nom arbitraire par erreur.
        if "/" in stored_filename or "\\" in stored_filename or ".." in stored_filename:
            raise ValueError("Nom de fichier stocké invalide.")
        resolved = (self.base_path / stored_filename).resolve()
        if self.base_path not in resolved.parents and resolved != self.base_path:
            raise ValueError("Chemin de fichier en dehors du répertoire de stockage.")
        return resolved

    def save(self, file_obj: BinaryIO, stored_filename: str) -> int:
        dest = self._safe_path(stored_filename)
        size = 0
        with open(dest, "wb") as out:
            shutil.copyfileobj(file_obj, out)
        size = dest.stat().st_size
        return size

    def open(self, stored_filename: str) -> BinaryIO:
        return open(self._safe_path(stored_filename), "rb")

    def delete(self, stored_filename: str) -> None:
        path = self._safe_path(stored_filename)
        if path.exists():
            path.unlink()

    def path_for(self, stored_filename: str) -> Path:
        return self._safe_path(stored_filename)
