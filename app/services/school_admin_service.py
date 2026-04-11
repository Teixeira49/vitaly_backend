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

    # ──────────────────────────────────────────────────────────
    # GET - Detalle completo de un estudiante
    # ──────────────────────────────────────────────────────────

    def get_student_detail(self, user_id: int, student_id: int) -> dict:
        school_id = self._get_school_id_for_admin(user_id)

        # 1. Verificar que el estudiante existe y no está eliminado
        student_res = (
            supabase.table("student")
            .select("id, name, lastname, birthday, gender, blood_type, identity_number, is_active, is_deleted")
            .eq("id", student_id)
            .eq("is_deleted", False)
            .execute()
        )
        if not student_res.data:
            raise HTTPException(status_code=404, detail=f"No existe ningún estudiante activo con ID {student_id}.")
        student = student_res.data[0]

        # 2. Verificar aislamiento de tenant: el estudiante debe estar registrado en un salón de ESTA escuela
        reg_res = (
            supabase.table("classroom_registration")
            .select("classroom_id")
            .eq("student_id", student_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not reg_res.data:
            raise HTTPException(
                status_code=403,
                detail="Este estudiante no está inscrito en ningún salón de tu escuela."
            )
        classroom_id = reg_res.data[0]["classroom_id"]
        cr_res = (
            supabase.table("classroom")
            .select("school_id")
            .eq("id", classroom_id)
            .execute()
        )
        if not cr_res.data or cr_res.data[0]["school_id"] != school_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para visualizar a este estudiante: pertenece a otra escuela."
            )

        # 3. Representantes: student_representative → parent → user
        sr_res = (
            supabase.table("student_representative")
            .select("parent_id")
            .eq("student_id", student_id)
            .eq("is_deleted", False)
            .execute()
        )
        representatives = []
        if sr_res.data:
            parent_ids = [r["parent_id"] for r in sr_res.data]
            for parent_id in parent_ids:
                parent_res = (
                    supabase.table("parent")
                    .select("id, user_id, occupation, type_representative, is_active")
                    .eq("id", parent_id)
                    .eq("is_deleted", False)
                    .execute()
                )
                if parent_res.data:
                    parent = parent_res.data[0]
                    # Traer datos básicos del user vinculado al representante
                    user_res = (
                        supabase.table("user")
                        .select("id, name, lastname, email, gender, address")
                        .eq("id", parent["user_id"])
                        .eq("is_deleted", False)
                        .execute()
                    )
                    parent["user_info"] = user_res.data[0] if user_res.data else None
                    representatives.append(parent)

        # 4. Información de salud (student_metrics)
        health_info = None
        metrics_res = (
            supabase.table("student_metrics")
            .select("height, weight, updated_at")
            .eq("student_id", student_id)
            .eq("is_deleted", False)
            .eq("is_current", True)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if metrics_res.data:
            metric = metrics_res.data[0]
            weight_kg: float = metric["weight"]
            height_m: float = metric["height"]

            if height_m and height_m > 0:
                bmi = round(weight_kg / (height_m ** 2), 2)
                if bmi < 18.5:
                    nutritional_status = "DESNUTRIDO"
                elif bmi <= 24.9:
                    nutritional_status = "OPTIMO"
                else:
                    nutritional_status = "OBESO"

                health_info = {
                    "weight_kg": weight_kg,
                    "height_m": height_m,
                    "bmi": bmi,
                    "nutritional_status": nutritional_status,
                    "measured_at": metric.get("updated_at"),
                }

        return {
            "student": student,
            "representatives": representatives if representatives else None,
            "health_info": health_info,
        }

    # ──────────────────────────────────────────────────────────
    # GET - Historial de métricas de un estudiante
    # ──────────────────────────────────────────────────────────

    def get_student_metrics_history(self, user_id: int, student_id: int, limit: int) -> dict | None:
        school_id = self._get_school_id_for_admin(user_id)

        # 1. Verificar que el estudiante existe y no está eliminado
        student_res = (
            supabase.table("student")
            .select("id")
            .eq("id", student_id)
            .eq("is_deleted", False)
            .execute()
        )
        if not student_res.data:
            raise HTTPException(status_code=404, detail=f"No existe ningún estudiante activo con ID {student_id}.")

        # 2. Verificar aislamiento de tenant: el estudiante pertenece a la escuela del admin
        reg_res = (
            supabase.table("classroom_registration")
            .select("classroom_id")
            .eq("student_id", student_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not reg_res.data:
            raise HTTPException(
                status_code=403,
                detail="Este estudiante no está inscrito en ningún salón de tu escuela."
            )
        classroom_id = reg_res.data[0]["classroom_id"]
        cr_res = (
            supabase.table("classroom")
            .select("school_id")
            .eq("id", classroom_id)
            .execute()
        )
        if not cr_res.data or cr_res.data[0]["school_id"] != school_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para visualizar a este estudiante: pertenece a otra escuela."
            )

        # 3. Obtener historial de métricas ordenadas por fecha de registro (más recientes primero)
        metrics_res = (
            supabase.table("student_metrics")
            .select("weight, height, updated_at")
            .eq("student_id", student_id)
            .eq("is_deleted", False)
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )

        if not metrics_res.data:
            return None

        # 4. Formatear la salida en series de tiempo separadas para peso y altura
        peso = []
        altura = []
        for m in metrics_res.data:
            fecha = m.get("updated_at")
            if m.get("weight") is not None:
                peso.append({"fecha": fecha, "valor": m["weight"]})
            if m.get("height") is not None:
                altura.append({"fecha": fecha, "valor": m["height"]})

        return {
            "peso": peso if peso else [],
            "altura": altura if altura else [],
        }


school_admin_service = SchoolAdminService()
