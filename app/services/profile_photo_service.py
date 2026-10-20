"""Ciclo de vida compartido de la foto de perfil (validación, almacenamiento en ImageKit y sincronización con la BD).

Lo usan todos los roles que tienen foto de perfil (médico, administrador de escuela)
para que las reglas de validación y las garantías de consistencia entre ImageKit
y la BD vivan en un solo lugar.
"""
import logging
from typing import BinaryIO, Optional
from fastapi import HTTPException, status

from app.core.database import supabase
from app.services.imagekit_service import imagekit_service

logger = logging.getLogger(__name__)

MAX_PROFILE_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB

# Tipo MIME canónico -> extensión con la que se almacena el archivo.
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
# Alias no estándar que envían algunos clientes.
_CONTENT_TYPE_ALIASES = {"image/jpg": "image/jpeg"}

SCHOOL_ADMIN_PHOTO_FOLDER = "/vitaly/profiles"
DOCTOR_PHOTO_FOLDER = "/vitaly/profiles/doctors"


def read_upload_capped(stream: BinaryIO) -> bytes:
    """Lee un archivo subido leyendo como máximo MAX_PROFILE_PHOTO_BYTES + 1 bytes.

    El byte adicional basta para detectar un archivo demasiado grande sin cargar
    en memoria una subida de tamaño arbitrario.

    Args:
        stream: Flujo binario de la subida (``UploadFile.file``).

    Returns:
        bytes: Contenido leído, de a lo sumo ``MAX_PROFILE_PHOTO_BYTES + 1`` bytes.
        Que supere el máximo es la señal de que el archivo es demasiado grande.
    """
    return stream.read(MAX_PROFILE_PHOTO_BYTES + 1)


def detect_image_type(file_bytes: bytes) -> Optional[str]:
    """Retorna el tipo MIME canónico según los magic bytes, o None si no está soportado.

    Inspecciona el contenido real del archivo en lugar de confiar en el
    Content-Type declarado por el cliente.

    Args:
        file_bytes: Contenido binario completo del archivo.

    Returns:
        Optional[str]: ``image/jpeg``, ``image/png`` o ``image/webp``; ``None`` si
        el contenido no corresponde a ninguno de los formatos soportados.
    """
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(file_bytes) >= 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_profile_photo(file_bytes: bytes, content_type: str) -> str:
    """Valida una foto de perfil subida y retorna la extensión con la que se almacenará.

    Args:
        file_bytes: Contenido binario del archivo, ya leído con
            :func:`read_upload_capped`.
        content_type: Content-Type declarado por el cliente. Debe coincidir con
            los magic bytes del contenido.

    Returns:
        str: Extensión canónica con la que se guardará el archivo (``jpg``,
        ``png`` o ``webp``).

    Raises:
        HTTPException(400): Archivo vacío, archivo mayor a 5 MB, content type
            declarado no soportado, o contenido que no es una imagen JPEG/PNG/WebP
            que coincida con el content type declarado.
    """
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo de imagen está vacío."
        )

    if len(file_bytes) > MAX_PROFILE_PHOTO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo excede el tamaño máximo permitido de 5 MB."
        )

    declared = (content_type or "").lower()
    declared = _CONTENT_TYPE_ALIASES.get(declared, declared)
    if declared not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato no permitido ({content_type}). Solo se admiten imágenes JPEG, PNG o WebP."
        )

    detected = detect_image_type(file_bytes)
    if detected is None or detected != declared:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no permitido: el contenido del archivo no es una imagen JPEG, PNG o WebP válida."
        )

    return ALLOWED_IMAGE_TYPES[detected]


def _get_current_photo_file_id(user_id: int) -> Optional[str]:
    """Obtiene el photo_file_id actual del usuario.

    Args:
        user_id: ID del usuario cuya foto se consulta.

    Returns:
        Optional[str]: ID del archivo en ImageKit, o ``None`` si el usuario no
        existe o no tiene foto registrada.

    Raises:
        HTTPException(500): Si falla la consulta a la BD.
    """
    try:
        res = (
            supabase.table("user")
            .select("photo_file_id")
            .eq("id", user_id)
            .execute()
        )
    except Exception:
        logger.exception("Error al consultar photo_file_id para user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al consultar la foto de perfil."
        )
    if not res.data:
        return None
    return res.data[0].get("photo_file_id")


def upload_profile_photo(user_id: int, file_bytes: bytes, content_type: str, folder: str) -> dict:
    """Valida, sube y persiste una nueva foto de perfil, reemplazando la anterior.

    Reglas de consistencia:
        - Si falla la actualización en la BD, se elimina el archivo recién subido a ImageKit.
        - Solo después de que la actualización en la BD tiene éxito se elimina el
          archivo anterior de ImageKit (best-effort).

    Args:
        user_id: ID del usuario dueño de la foto.
        file_bytes: Contenido binario de la imagen ya leído de la subida.
        content_type: Content-Type declarado por el cliente.
        folder: Carpeta destino en ImageKit; depende del rol (ver
            ``SCHOOL_ADMIN_PHOTO_FOLDER`` y ``DOCTOR_PHOTO_FOLDER``).

    Returns:
        dict: {'photo_url': <nueva URL pública>}

    Raises:
        HTTPException(400): Archivo inválido o la actualización en la BD no afectó filas.
        HTTPException(500): ImageKit no está configurado o falló el acceso a la BD.
        HTTPException(502): Falló la subida a ImageKit.
    """
    extension = validate_profile_photo(file_bytes, content_type)
    previous_file_id = _get_current_photo_file_id(user_id)

    uploaded = imagekit_service.upload_profile_image(
        file_bytes=file_bytes,
        extension=extension,
        user_id=user_id,
        folder=folder,
    )

    try:
        update_res = (
            supabase.table("user")
            .update({"photo_url": uploaded.url, "photo_file_id": uploaded.file_id})
            .eq("id", user_id)
            .execute()
        )
    except Exception:
        logger.exception(
            "Error al actualizar photo_url en la BD para user_id=%s; revirtiendo la subida a ImageKit",
            user_id,
        )
        imagekit_service.delete_file(uploaded.file_id, user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar la foto de perfil."
        )

    if not update_res.data:
        imagekit_service.delete_file(uploaded.file_id, user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo actualizar la foto de perfil en la base de datos."
        )

    if previous_file_id and previous_file_id != uploaded.file_id:
        imagekit_service.delete_file(previous_file_id, user_id=user_id)

    return {"photo_url": uploaded.url}


def delete_profile_photo(user_id: int) -> dict:
    """Limpia la foto de perfil del usuario en la BD y luego la elimina de ImageKit (best-effort).

    Args:
        user_id: ID del usuario cuya foto se desea eliminar.

    Returns:
        dict: {'photo_url': None}

    Raises:
        HTTPException(400): La actualización en la BD no afectó filas.
        HTTPException(500): Falló el acceso a la BD.
    """
    previous_file_id = _get_current_photo_file_id(user_id)

    try:
        update_res = (
            supabase.table("user")
            .update({"photo_url": None, "photo_file_id": None})
            .eq("id", user_id)
            .execute()
        )
    except Exception:
        logger.exception("Error al eliminar photo_url en la BD para user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar la foto de perfil."
        )

    if not update_res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo eliminar la foto de perfil en la base de datos."
        )

    imagekit_service.delete_file(previous_file_id, user_id=user_id)
    return {"photo_url": None}
