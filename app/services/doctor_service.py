import logging
from typing import Optional
from fastapi import HTTPException, status

from app.core.database import supabase
from app.services.imagekit_service import imagekit_service

logger = logging.getLogger(__name__)


class DoctorService:
    """Servicio para la gestión del perfil e información de médicos (rol doctor)."""

    def get_my_profile(self, user_id: int) -> dict:
        """Obtiene el perfil completo del médico autenticado.

        Incluye datos personales del usuario, información profesional del doctor
        y la lista de escuelas a las que se encuentra vinculado.

        Args:
            user_id (int): Identificador del usuario en la tabla 'user'.

        Returns:
            dict: Estructura con 'user_info', 'doctor_info' y 'schools'.

        Raises:
            HTTPException: 404 si no se encuentra el perfil de médico asociado al usuario.
        """
        doc_res = (
            supabase.table("doctor")
            .select("*, user(*), doctor_to_school(*, school(*))")
            .eq("user_id", user_id)
            .execute()
        )
        if not doc_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil de médico no encontrado."
            )

        doctor_data = doc_res.data[0]
        user_info = doctor_data.pop("user", {}) or {}
        raw_schools = doctor_data.pop("doctor_to_school", []) or []

        # Seguridad: remover contraseña de los datos del usuario
        if "password" in user_info:
            del user_info["password"]

        # Manejo de valores por defecto legibles
        user_info["gender"] = user_info.get("gender") or "No especificado"
        user_info["address"] = user_info.get("address") or "Dirección desconocida"
        user_info["biography"] = user_info.get("biography") or "Sin biografía"
        user_info["identity_number"] = user_info.get("identity_number") or "N/A"
        user_info["photo_url"] = user_info.get("photo_url")

        # Formatear lista de escuelas asociadas
        schools = []
        for d2s in raw_schools:
            school_item = d2s.get("school") or {}
            schools.append({
                "school_id": d2s.get("school_id"),
                "status": d2s.get("status"),
                "school_name": school_item.get("name") or "Escuela desconocida",
                "school_address": school_item.get("address") or "Dirección no disponible",
                "school_rif": school_item.get("rif"),
            })

        return {
            "user_info": user_info,
            "doctor_info": doctor_data,
            "schools": schools
        }

    def update_my_profile(self, user_id: int, payload: dict) -> dict:
        """Actualiza la información personal del médico en la tabla 'user'.

        Args:
            user_id (int): Identificador del usuario autenticado.
            payload (dict): Diccionario de campos validados a actualizar.

        Returns:
            dict: Perfil completo actualizado del médico.

        Raises:
            HTTPException: 400 si la actualización en base de datos falla.
        """
        if not payload:
            return self.get_my_profile(user_id)

        update_data = payload.copy()

        # Si viene birthday (date), convertir a formato ISO
        if "birthday" in update_data and hasattr(update_data["birthday"], "isoformat"):
            update_data["birthday"] = update_data["birthday"].isoformat()

        update_res = (
            supabase.table("user")
            .update(update_data)
            .eq("id", user_id)
            .execute()
        )

        if not update_res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo actualizar el perfil del médico."
            )

        return self.get_my_profile(user_id)

    def upload_my_profile_photo(
        self,
        user_id: int,
        file_bytes: bytes,
        filename: str,
        content_type: str
    ) -> dict:
        """Sube la foto de perfil del médico a ImageKit y actualiza photo_url en la BD.

        Args:
            user_id (int): Identificador del usuario en la tabla 'user'.
            file_bytes (bytes): Contenido binario del archivo de imagen.
            filename (str): Nombre del archivo original.
            content_type (str): MIME-type del archivo recibido.

        Returns:
            dict: Diccionario con la clave 'photo_url' y la URL generada.

        Raises:
            HTTPException: 400 si el archivo no es válido (formato o tamaño).
            HTTPException: 500 si ImageKit no está configurado.
            HTTPException: 502 si falla la subida al servicio ImageKit.
        """
        allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
        if not content_type or content_type.lower() not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato no permitido ({content_type}). Solo se admiten imágenes JPEG, PNG o WebP."
            )

        max_size = 5 * 1024 * 1024  # 5 MB
        if len(file_bytes) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo excede el tamaño máximo permitido de 5 MB."
            )

        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo de imagen está vacío."
            )

        photo_url = imagekit_service.upload_profile_image(
            file_bytes=file_bytes,
            original_filename=filename,
            user_id=user_id,
            folder="/vitaly/profiles/doctors"
        )

        update_res = (
            supabase.table("user")
            .update({"photo_url": photo_url})
            .eq("id", user_id)
            .execute()
        )

        if not update_res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo actualizar la foto de perfil en la base de datos."
            )

        return {"photo_url": photo_url}

    def delete_my_profile_photo(self, user_id: int) -> dict:
        """Elimina la foto de perfil del médico autenticado estableciendo photo_url en None.

        Args:
            user_id (int): Identificador del usuario en la tabla 'user'.

        Returns:
            dict: Diccionario con la clave 'photo_url' en None.

        Raises:
            HTTPException: 400 si no se pudo actualizar el registro en la base de datos.
        """
        update_res = (
            supabase.table("user")
            .update({"photo_url": None})
            .eq("id", user_id)
            .execute()
        )

        if not update_res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo eliminar la foto de perfil en la base de datos."
            )

        return {"photo_url": None}


doctor_service = DoctorService()
