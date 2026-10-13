"""
Validation des fichiers téléversés : extension autorisée, taille maximale, et
signature binaire réelle du contenu (pas seulement l'extension ou le
Content-Type déclaré, qui peuvent être falsifiés par le client — "ne jamais
faire confiance aux données envoyées par le navigateur").
"""
import uuid
from dataclasses import dataclass
from typing import Optional

# Extension -> (mime_type affiché, signatures binaires acceptées).
# Une signature est un tuple (offset, octets_attendus). Plusieurs signatures
# possibles pour un même format (ex: docx/xlsx/pptx sont tous des zip OOXML,
# donc distingués seulement par extension déclarée + structure zip valide).
ZIP_SIGNATURES = [(0, b"PK\x03\x04"), (0, b"PK\x05\x06"), (0, b"PK\x07\x08")]
OLE_SIGNATURE = [(0, b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")]  # doc/xls/ppt "legacy"

ALLOWED_EXTENSIONS: dict[str, dict] = {
    "pdf": {"mime": "application/pdf", "signatures": [(0, b"%PDF-")]},
    "doc": {"mime": "application/msword", "signatures": OLE_SIGNATURE},
    "docx": {
        "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "signatures": ZIP_SIGNATURES,
    },
    "xls": {"mime": "application/vnd.ms-excel", "signatures": OLE_SIGNATURE},
    "xlsx": {
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "signatures": ZIP_SIGNATURES,
    },
    "ppt": {"mime": "application/vnd.ms-powerpoint", "signatures": OLE_SIGNATURE},
    "pptx": {
        "mime": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "signatures": ZIP_SIGNATURES,
    },
    "jpg": {"mime": "image/jpeg", "signatures": [(0, b"\xff\xd8\xff")]},
    "jpeg": {"mime": "image/jpeg", "signatures": [(0, b"\xff\xd8\xff")]},
    "png": {"mime": "image/png", "signatures": [(0, b"\x89PNG\r\n\x1a\n")]},
    "webp": {"mime": "image/webp", "signatures": [(0, b"RIFF"), (8, b"WEBP")]},
    "zip": {"mime": "application/zip", "signatures": ZIP_SIGNATURES},
}

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


class FileValidationError(Exception):
    pass


@dataclass
class ValidatedFile:
    extension: str
    mime_type: str
    stored_filename: str


def _extension_of(original_filename: str) -> str:
    if "." not in original_filename:
        raise FileValidationError("Le fichier doit avoir une extension.")
    return original_filename.rsplit(".", 1)[-1].lower()


def _signature_matches(header: bytes, signatures: list[tuple[int, bytes]]) -> bool:
    return any(header[offset : offset + len(sig)] == sig for offset, sig in signatures)


def validate_upload(
    *, original_filename: str, header_bytes: bytes, declared_size: Optional[int], max_size_bytes: int
) -> ValidatedFile:
    extension = _extension_of(original_filename)
    spec = ALLOWED_EXTENSIONS.get(extension)
    if spec is None:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise FileValidationError(f"Type de fichier non autorisé (.{extension}). Formats acceptés : {allowed}.")

    if declared_size is not None and declared_size > max_size_bytes:
        raise FileValidationError(f"Fichier trop volumineux (max {max_size_bytes // (1024 * 1024)} Mo).")

    # Vérification de la signature binaire réelle : une attaque classique
    # consiste à renommer un exécutable ou un script en .pdf/.jpg — l'extension
    # seule ne protège de rien.
    signatures = spec["signatures"]
    if signatures and not _signature_matches(header_bytes, signatures):
        raise FileValidationError(
            "Le contenu du fichier ne correspond pas à son extension déclarée. "
            "Le fichier est peut-être corrompu ou d'un type différent de ce qu'il prétend être."
        )

    stored_filename = f"{uuid.uuid4().hex}.{extension}"
    return ValidatedFile(extension=extension, mime_type=spec["mime"], stored_filename=stored_filename)
