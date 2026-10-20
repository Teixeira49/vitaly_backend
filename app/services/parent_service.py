"""Servicio del rol representante: vinculación automática con sus estudiantes."""

from fastapi import HTTPException, status
from app.core.database import supabase
from typing import List, Optional


class ParentService:
    """Vinculación entre representantes y los estudiantes que tienen autorizados."""

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
