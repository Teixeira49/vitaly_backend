"""Servicio del rol médico: perfil propio y foto de perfil."""

import logging
from typing import Optional
from fastapi import HTTPException, status

from app.core.database import supabase
from app.services import profile_photo_service

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

        # Seguridad: remover contraseña e identificador interno de ImageKit
        user_info.pop("password", None)
        user_info.pop("photo_file_id", None)

        # Manejo de valores por defecto legibles
        user_info["gender"] = user_info.get("gender") or "No especificado"
        user_info["address"] = user_info.get("address") or "Dirección desconocida"
        user_info["biography"] = user_info.get("biography") or "Sin biografía"
        user_info["identity_number"] = user_info.get("identity_number") or "N/A"

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

    def upload_my_profile_photo(self, user_id: int, file_bytes: bytes, content_type: str) -> dict:
        """Sube la foto de perfil del médico a ImageKit y actualiza photo_url en la BD.

        Delega la validación y el ciclo de vida en ImageKit/BD a
        ``profile_photo_service``, fijando la carpeta propia de los médicos.

        Args:
            user_id: ID del médico autenticado (claim ``sub`` del JWT).
            file_bytes: Contenido binario de la imagen ya leído de la subida.
            content_type: Content-Type declarado por el cliente; se contrasta con
                los magic bytes del archivo.

        Returns:
            dict: Diccionario con la clave 'photo_url' y la URL generada.

        Raises:
            HTTPException: 400 si el archivo es inválido o supera el tamaño máximo.
            HTTPException: 500 si ImageKit no está configurado o falla la BD.
            HTTPException: 502 si falla la subida a ImageKit.
        """
        return profile_photo_service.upload_profile_photo(
            user_id=user_id,
            file_bytes=file_bytes,
            content_type=content_type,
            folder=profile_photo_service.DOCTOR_PHOTO_FOLDER,
        )

    def delete_my_profile_photo(self, user_id: int) -> dict:
        """Elimina la foto de perfil del médico autenticado (BD e ImageKit).

        Args:
            user_id: ID del médico autenticado (claim ``sub`` del JWT).

        Returns:
            dict: Diccionario con la clave 'photo_url' en None.

        Raises:
            HTTPException: 400 si la actualización en la BD no afectó filas.
            HTTPException: 500 si falla el acceso a la BD.
        """
        return profile_photo_service.delete_profile_photo(user_id=user_id)


#: Instancia compartida del servicio, importada por los endpoints de médico.
doctor_service = DoctorService()
