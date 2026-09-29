import logging
import uuid
from typing import Optional
from fastapi import HTTPException, status
from imagekitio import ImageKit

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ImageKitService:
    """Servicio para la integración con ImageKit.io para almacenamiento de multimedia."""

    def __init__(self) -> None:
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
            )
        return self._client

    def upload_profile_image(
        self,
        file_bytes: bytes,
        original_filename: str,
        user_id: int,
        folder: str = "/vitaly/profiles"
    ) -> str:
        """Sube una imagen de perfil a ImageKit.io y retorna la URL pública generada.

        Args:
            file_bytes (bytes): Contenido binario del archivo de imagen.
            original_filename (str): Nombre original del archivo para preservar extensión.
            user_id (int): Identificador del usuario que sube la foto.
            folder (str, optional): Carpeta de destino en el bucket de ImageKit. Defaults to "/vitaly/profiles".

        Returns:
            str: URL pública de la imagen alojada en ImageKit.

        Raises:
            HTTPException: Si falla la inicialización o la subida a ImageKit.
        """
        client = self._get_client()

        # Extraer extensión o usar .jpg por defecto
        ext = "jpg"
        if "." in original_filename:
            ext = original_filename.rsplit(".", 1)[-1].lower()

        clean_filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}.{ext}"

        try:
            logger.info("Subiendo imagen de perfil a ImageKit para user_id=%s con nombre=%s", user_id, clean_filename)
            upload_response = client.files.upload(
                file=file_bytes,
                file_name=clean_filename,
                folder=folder,
                use_unique_file_name=True,
            )
            return upload_response.url
        except Exception as e:
            logger.exception("Error al subir archivo a ImageKit: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al subir la imagen al bucket de almacenamiento: {str(e)}"
            )


imagekit_service = ImageKitService()
