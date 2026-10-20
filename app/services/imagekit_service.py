"""Integración con ImageKit.io para el almacenamiento de imágenes."""

import logging
import uuid
from dataclasses import dataclass
from typing import Optional
from fastapi import HTTPException, status
from imagekitio import ImageKit

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass(frozen=True)
class UploadedImage:
    """Resultado de una subida exitosa a ImageKit."""
    url: str
    file_id: str


class ImageKitService:
    """Servicio para la integración con ImageKit.io para almacenamiento de multimedia."""

    def __init__(self) -> None:
        """Construye el servicio sin contactar ImageKit todavía.

        El cliente se inicializa de forma perezosa en :meth:`_get_client`, para que
        la aplicación arranque aunque las credenciales no estén configuradas.
        """
        self._client: Optional[ImageKit] = None

    def _get_client(self) -> ImageKit:
        """Obtiene o inicializa el cliente de ImageKit.

        Returns:
            ImageKit: Instancia del cliente ImageKit.

        Raises:
            HTTPException: Si las credenciales de ImageKit no están configuradas en el entorno.
        """
        if not settings.IMAGEKIT_PRIVATE_KEY:
            logger.error("IMAGEKIT_PRIVATE_KEY no está configurada en las variables de entorno.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El servicio de almacenamiento de imágenes (ImageKit) no está configurado en el servidor."
            )

        if self._client is None:
            self._client = ImageKit(
                private_key=settings.IMAGEKIT_PRIVATE_KEY,
                timeout=settings.IMAGEKIT_TIMEOUT_SECONDS,
                max_retries=settings.IMAGEKIT_MAX_RETRIES,
            )
        return self._client

    def upload_profile_image(
        self,
        file_bytes: bytes,
        extension: str,
        user_id: int,
        folder: str,
    ) -> UploadedImage:
        """Sube una imagen de perfil a ImageKit.io.

        Args:
            file_bytes (bytes): Contenido de la imagen, ya validado.
            extension (str): Extensión derivada del tipo de imagen detectado
                (nunca del nombre de archivo enviado por el cliente).
            user_id (int): Dueño de la foto, usado para construir el nombre del archivo.
            folder (str): Carpeta de destino en ImageKit.

        Returns:
            UploadedImage: URL pública e id de archivo de ImageKit de la imagen almacenada.

        Raises:
            HTTPException(500): Si ImageKit no está configurado.
            HTTPException(502): Si falla la subida a ImageKit.
        """
        client = self._get_client()
        clean_filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}.{extension}"

        try:
            logger.info("Subiendo imagen de perfil a ImageKit para user_id=%s como %s", user_id, clean_filename)
            upload_response = client.files.upload(
                file=file_bytes,
                file_name=clean_filename,
                folder=folder,
                use_unique_file_name=True,
            )
        except Exception:
            logger.exception("Error al subir la imagen a ImageKit para user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Error al subir la imagen al bucket de almacenamiento."
            )

        if not upload_response.url or not upload_response.file_id:
            logger.error("La subida a ImageKit para user_id=%s no retornó url ni file_id", user_id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Error al subir la imagen al bucket de almacenamiento."
            )

        return UploadedImage(url=upload_response.url, file_id=upload_response.file_id)

    def delete_file(self, file_id: Optional[str], user_id: Optional[int] = None) -> None:
        """Elimina un archivo de ImageKit (best-effort).

        Nunca lanza excepciones: cualquier fallo (incluida la falta de configuración)
        se registra en el log y se ignora, para que los llamadores puedan usarlo como
        limpieza sin ocultar el resultado principal de la petición.

        Args:
            file_id (Optional[str]): Id del archivo en ImageKit. No hace nada si está vacío.
            user_id (Optional[int]): Dueño del archivo, solo para contexto en los logs.
        """
        if not file_id:
            return
        try:
            self._get_client().files.delete(file_id)
            logger.info("Archivo de ImageKit eliminado file_id=%s user_id=%s", file_id, user_id)
        except Exception:
            logger.exception(
                "No se pudo eliminar el archivo de ImageKit file_id=%s user_id=%s (se ignora)",
                file_id,
                user_id,
            )


imagekit_service = ImageKitService()
