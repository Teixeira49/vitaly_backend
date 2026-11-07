"""Servicio del rol representante: perfil propio, foto de perfil y vinculación con sus estudiantes."""

import logging

from fastapi import HTTPException, status
from app.core.database import supabase
from app.services import profile_photo_service

logger = logging.getLogger(__name__)

# Columnas del perfil propio. Se enumeran explícitamente para que la contraseña y
# el photo_file_id de ImageKit nunca salgan de la base de datos.
_PROFILE_COLUMNS = (
    "id, user_id, occupation, type_representative, "
    "user(email, name, lastname, identity_number, birthday, gender, address, photo_url)"
)
# Campos editables de ParentProfileUpdate, agrupados por la tabla en la que viven.
_USER_EDITABLE_FIELDS = ("name", "lastname", "birthday", "gender", "address")
_PARENT_EDITABLE_FIELDS = ("occupation", "type_representative")


class ParentService:
    """Perfil propio del representante y su vinculación con los estudiantes autorizados."""

    def get_my_profile(self, user_id: int) -> dict:
        """Obtiene el perfil del representante autenticado.

        Combina los datos personales de ``user`` con los de ``parent`` (ocupación y
        parentesco) en una estructura plana que coincide con ``ParentProfileRead``.

        Args:
            user_id: ID del representante autenticado (claim ``sub`` del JWT).

        Returns:
            dict: Perfil con ``id`` (de ``parent``), ``user_id``, datos personales,
            ``photo_url``, ``occupation`` y ``type_representative``. Nunca incluye
            ``password`` ni ``photo_file_id``.

        Raises:
            HTTPException: 404 si el usuario no tiene un perfil de representante activo.
            HTTPException: 500 si falla la consulta a la BD.
        """
        try:
            parent_res = (
                supabase.table("parent")
                .select(_PROFILE_COLUMNS)
                .eq("user_id", user_id)
                .eq("is_deleted", False)
                .execute()
            )
        except Exception:
            logger.exception("Error al consultar el perfil de representante para user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al consultar el perfil del representante."
            )

        if not parent_res.data or not parent_res.data[0].get("user"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró un perfil de representante asociado a este usuario."
            )

        parent_data = parent_res.data[0]
        user_info = parent_data["user"]
        return {
            "id": parent_data["id"],
            "user_id": parent_data["user_id"],
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "lastname": user_info.get("lastname"),
            "identity_number": user_info.get("identity_number"),
            "birthday": user_info.get("birthday"),
            "gender": user_info.get("gender"),
            "address": user_info.get("address"),
            "photo_url": user_info.get("photo_url"),
            "occupation": parent_data.get("occupation"),
            "type_representative": parent_data.get("type_representative"),
        }

    def update_my_profile(self, user_id: int, payload: dict) -> dict:
        """Actualiza los datos editables del representante en ``user`` y ``parent``.

        Solo se escriben los campos enviados. Email, rol, contraseña, foto y
        documento de identidad no son editables por esta vía (ver
        ``ParentProfileUpdate``).

        Las dos tablas se actualizan en llamadas separadas (supabase-py no ofrece
        transacciones multi-tabla): si falla la segunda, los cambios de ``user`` ya
        aplicados se conservan. Mismo compromiso que el resto de perfiles; la
        atomicidad real requeriría una función de Postgres invocada con ``.rpc()``.

        Args:
            user_id: ID del representante autenticado (claim ``sub`` del JWT).
            payload: Campos validados por ``ParentProfileUpdate``, ya serializados
                (``model_dump(exclude_unset=True, mode="json")``).

        Returns:
            dict: Perfil completo actualizado (ver :meth:`get_my_profile`).

        Raises:
            HTTPException: 404 si el usuario no tiene un perfil de representante activo.
            HTTPException: 400 si alguna actualización no afectó filas.
            HTTPException: 500 si falla el acceso a la BD.
        """
        current = self.get_my_profile(user_id)

        user_fields = {k: payload[k] for k in _USER_EDITABLE_FIELDS if k in payload}
        parent_fields = {k: payload[k] for k in _PARENT_EDITABLE_FIELDS if k in payload}
        if not user_fields and not parent_fields:
            return current

        if user_fields:
            self._update_row("user", user_fields, id=user_id)
        if parent_fields:
            self._update_row("parent", parent_fields, id=current["id"], user_id=user_id)

        return self.get_my_profile(user_id)

    def _update_row(self, table: str, values: dict, **filters) -> None:
        """Actualiza una fila del perfil filtrando por igualdad y valida que exista.

        Args:
            table: Tabla a actualizar (``user`` o ``parent``).
            values: Columnas y valores a escribir.
            **filters: Pares columna=valor encadenados como ``.eq(...)``.

        Raises:
            HTTPException: 400 si la actualización no afectó filas.
            HTTPException: 500 si falla el acceso a la BD.
        """
        try:
            query = supabase.table(table).update(values)
            for column, value in filters.items():
                query = query.eq(column, value)
            update_res = query.execute()
        except Exception:
            logger.exception("Error al actualizar '%s' del perfil de representante (%s)", table, filters)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar el perfil del representante."
            )

        if not update_res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo actualizar el perfil del representante."
            )

    def upload_my_profile_photo(self, user_id: int, file_bytes: bytes, content_type: str) -> dict:
        """Sube la foto de perfil del representante a ImageKit y actualiza photo_url en la BD.

        Delega la validación y el ciclo de vida en ImageKit/BD a
        ``profile_photo_service``, fijando la carpeta propia de los representantes.

        Args:
            user_id: ID del representante autenticado (claim ``sub`` del JWT).
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
            folder=profile_photo_service.PARENT_PHOTO_FOLDER,
        )

    def delete_my_profile_photo(self, user_id: int) -> dict:
        """Elimina la foto de perfil del representante autenticado (BD e ImageKit).

        Args:
            user_id: ID del representante autenticado (claim ``sub`` del JWT).

        Returns:
            dict: Diccionario con la clave 'photo_url' en None.

        Raises:
            HTTPException: 400 si la actualización en la BD no afectó filas.
            HTTPException: 500 si falla el acceso a la BD.
        """
        return profile_photo_service.delete_profile_photo(user_id=user_id)

    def link_students_by_identity(self, user_id: int, identity_number: str) -> dict:
        """Vincula a un representante con los estudiantes que lo autorizaron.

        Busca los estudiantes cuyo campo ``authorization_number`` contiene el
        documento de identidad del representante y crea la relación en
        ``student_representative``. Se invoca durante el registro del representante
        y es idempotente: las vinculaciones ya existentes se reportan aparte en
        lugar de duplicarse.

        Args:
            user_id: ID del usuario representante (claim ``sub`` del JWT).
            identity_number: Documento de identidad del representante, usado como
                clave de búsqueda contra ``student.authorization_number``.

        Returns:
            dict: ``linked_students`` (vinculados ahora), ``already_linked`` (que ya
            lo estaban) y ``message`` con el resumen. Si no hubo coincidencias,
            ``linked_students`` viene vacío y no se incluye ``already_linked``.

        Raises:
            HTTPException: 404 si el usuario no tiene un perfil de representante.
        """
        # 1. Obtener el parent_id a partir del user_id
        parent_response = supabase.table("parent").select("id").eq("user_id", user_id).execute()
        if not parent_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró un perfil de representante asociado a este usuario."
            )
        parent_id = parent_response.data[0]["id"]

        # 2. Buscar estudiantes que tengan este identity_number en su authorization_number
        students_response = supabase.table("student") \
            .select("id, name, lastname") \
            .contains("authorization_number", [identity_number]) \
            .eq("is_deleted", False) \
            .execute()

        if not students_response.data:
            return {
                "linked_students": [],
                "message": "No se encontraron estudiantes autorizados con este número de identidad."
            }

        # 3. Crear las relaciones en student_representative (evitando duplicados)
        linked = []
        already_linked = []

        for student in students_response.data:
            # Verificar si ya existe la relación
            existing = supabase.table("student_representative") \
                .select("id") \
                .eq("student_id", student["id"]) \
                .eq("parent_id", parent_id) \
                .eq("is_deleted", False) \
                .execute()

            if existing.data:
                already_linked.append({
                    "student_id": student["id"],
                    "name": f"{student['name']} {student['lastname']}"
                })
                continue

            # Crear nueva vinculación
            supabase.table("student_representative").insert({
                "student_id": student["id"],
                "parent_id": parent_id,
                "is_deleted": False
            }).execute()

            linked.append({
                "student_id": student["id"],
                "name": f"{student['name']} {student['lastname']}"
            })

        return {
            "linked_students": linked,
            "already_linked": already_linked,
            "message": f"Se vincularon {len(linked)} estudiante(s). {len(already_linked)} ya estaban vinculados."
        }


#: Instancia compartida del servicio, importada por los endpoints de representante.
parent_service = ParentService()
