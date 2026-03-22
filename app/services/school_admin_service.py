from fastapi import HTTPException
from app.core.database import supabase


class SchoolAdminService:

    def _get_school_id_for_admin(self, user_id: int) -> int:
        """Obtiene el school_id vinculado al usuario admin_escuela. Lanza 403 si no está vinculado."""
        sa_response = (
            supabase.table("school_administrator")
            .select("school_id")
            .eq("user_id", user_id)
            .execute()
        )
        if not sa_response.data or sa_response.data[0].get("school_id") is None:
            raise HTTPException(
                status_code=403,
                detail="Tu usuario no está vinculado a ninguna escuela."
            )
        return sa_response.data[0]["school_id"]

    # ──────────────────────────────────────────────────────────
    # GET - Students Resume (Métricas)
    # ──────────────────────────────────────────────────────────

    def get_students_resume(self, user_id: int) -> dict:
        school_id = self._get_school_id_for_admin(user_id)

        # Obtener todos los estudiantes activos vinculados a esta escuela mediante classroom_registration
        # Paso 1: obtener ids de classrooms que pertenecen a esta escuela
        classrooms_res = (
            supabase.table("classroom")
            .select("id")
            .eq("school_id", school_id)
            .eq("is_deleted", False)
            .execute()
        )
        classroom_ids = [c["id"] for c in classrooms_res.data] if classrooms_res.data else []

        if not classroom_ids:
            return {
                "total_students": 0,
                "overweight_students": 0,
                "malnourished_students": 0,
                "active_cases": 0,
                "optimal_students": 0,
            }

        # Paso 2: obtener student_ids únicos registrados en esas clases
        regs_res = (
            supabase.table("classroom_registration")
            .select("student_id")
            .in_("classroom_id", classroom_ids)
            .execute()
        )
        student_ids = list({r["student_id"] for r in regs_res.data}) if regs_res.data else []
        total_students = len(student_ids)

        # ── SOBREPESO ──────────────────────────────────────────
        # TODO: Implementar lógica de detección de sobrepeso usando la tabla
        # `student_metrics` (campos: height, weight, is_current) para calcular
        # el IMC de cada estudiante y compararlo con los rangos pediátricos estándar.
        overweight_students = 0

        # ── DESNUTRICIÓN ───────────────────────────────────────
        # TODO: Implementar lógica de detección de desnutrición usando la tabla
        # `student_metrics` (campos: height, weight, is_current) para calcular
        # el IMC de cada estudiante y compararlo con los umbrales de desnutrición.
        malnourished_students = 0

        # ── CASOS ACTIVOS ──────────────────────────────────────
        # TODO: Implementar lógica para contar casos médicos activos desde la
        # tabla `medical_case`, filtrando por student_id de esta escuela donde
        # `end_date` IS NULL o is_deleted = false y aún no tiene fecha de cierre.
        active_cases = 0

        optimal_students = total_students - overweight_students - malnourished_students

        return {
            "total_students": total_students,
            "overweight_students": overweight_students,
            "malnourished_students": malnourished_students,
            "active_cases": active_cases,
            "optimal_students": optimal_students,
        }

    # ──────────────────────────────────────────────────────────
    # GET - Grados Académicos (Classrooms de la escuela)
    # ──────────────────────────────────────────────────────────

    def get_academic_grades(self, user_id: int, page: int, size: int) -> dict:
        school_id = self._get_school_id_for_admin(user_id)

        # Buscar el año académico vigente
        ay_res = (
            supabase.table("academic_year")
            .select("id, name")
            .eq("is_current", True)
            .eq("is_deleted", False)
            .limit(1)
            .execute()
        )
        if not ay_res.data:
            raise HTTPException(
                status_code=404,
                detail="No hay un año académico vigente configurado en el sistema."
            )
        current_academic_year = ay_res.data[0]
        academic_year_id = current_academic_year["id"]

        # Contar total de classrooms de esta escuela en el año vigente
        count_res = (
            supabase.table("classroom")
            .select("id", count="exact")
            .eq("school_id", school_id)
            .eq("academic_year_id", academic_year_id)
            .eq("is_deleted", False)
            .execute()
        )
        total = count_res.count or 0
        if total == 0:
            raise HTTPException(
                status_code=404,
                detail="Esta escuela no tiene grados registrados para el año académico vigente."
            )

        offset = (page - 1) * size
        rows = (
            supabase.table("classroom")
            .select("id, category, level, section, is_deleted")
            .eq("school_id", school_id)
            .eq("academic_year_id", academic_year_id)
            .eq("is_deleted", False)
            .order("category")
            .order("level")
            .range(offset, offset + size - 1)
            .execute()
        )

        # Enriquecer con el nombre del año académico
        enriched = []
        for c in rows.data:
            c["academic_year"] = current_academic_year
            enriched.append(c)

        return {
            "data": enriched,
            "total": total,
            "page": page,
            "size": size,
            "academic_year": current_academic_year,
        }

    # ──────────────────────────────────────────────────────────
    # GET - Estudiantes de un grado (classroom) específico
    # ──────────────────────────────────────────────────────────

    def get_students_by_classroom(self, user_id: int, classroom_id: int, page: int, size: int) -> dict:
        school_id = self._get_school_id_for_admin(user_id)

        # Verificar que el classroom pertenece a la misma escuela del admin
        classroom_res = (
            supabase.table("classroom")
            .select("id, school_id, category, level, section, academic_year_id")
            .eq("id", classroom_id)
            .eq("is_deleted", False)
            .execute()
        )
        if not classroom_res.data:
            raise HTTPException(status_code=404, detail=f"No existe ningún salón con ID {classroom_id}.")

        classroom = classroom_res.data[0]
        if classroom["school_id"] != school_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para acceder a los estudiantes de este salón: pertenece a otra escuela."
            )

        # Obtener registros de classroom_registration para ese classroom
        count_res = (
            supabase.table("classroom_registration")
            .select("student_id", count="exact")
            .eq("classroom_id", classroom_id)
            .execute()
        )
        total = count_res.count or 0
        if total == 0:
            raise HTTPException(
                status_code=404,
                detail=f"El salón con ID {classroom_id} no tiene estudiantes registrados."
            )

        offset = (page - 1) * size
        regs_res = (
            supabase.table("classroom_registration")
            .select("student_id")
            .eq("classroom_id", classroom_id)
            .range(offset, offset + size - 1)
            .execute()
        )
        student_ids = [r["student_id"] for r in regs_res.data]

        # Traer los datos de los estudiantes
        students_res = (
            supabase.table("student")
            .select("id, name, lastname, birthday, gender, blood_type, identity_number, is_active, is_deleted")
            .in_("id", student_ids)
            .execute()
        )

        return {
            "classroom": classroom,
            "data": students_res.data,
            "total": total,
            "page": page,
            "size": size,
        }


school_admin_service = SchoolAdminService()
