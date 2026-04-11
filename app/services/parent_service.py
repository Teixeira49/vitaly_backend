from fastapi import HTTPException, status
from app.core.database import supabase
from typing import List, Optional


class ParentService:
    def link_students_by_identity(self, user_id: int, identity_number: str) -> dict:
        """
        Busca en la tabla student los estudiantes cuyo campo authorization_number
        contiene el identity_number del representante. Si hay coincidencias,
        crea los registros correspondientes en student_representative.

        Retorna un resumen con los estudiantes vinculados.
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


parent_service = ParentService()
