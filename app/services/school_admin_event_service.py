from fastapi import HTTPException
from app.core.database import supabase
from datetime import datetime, date
from calendar import monthrange


class SchoolAdminEventService:

    # ──────────────────────────────────────────────────────────
    # Helpers internos
    # ──────────────────────────────────────────────────────────

    def _get_admin_record(self, user_id: int) -> dict:
        """Obtiene el registro completo del school_administrator vinculado al user_id.
        Retorna un dict con sch_admin_id y school_id. Lanza 403 si no existe."""
        sa_res = (
            supabase.table("school_administrator")
            .select("sch_admin_id, school_id")
            .eq("user_id", user_id)
            .execute()
        )
        if not sa_res.data:
            raise HTTPException(
                status_code=403,
                detail="Tu usuario no está vinculado a ninguna escuela."
            )
        return sa_res.data[0]

    def _get_school_classroom_ids(self, school_id: int) -> list[int]:
        """Retorna los IDs de todos los classrooms activos de una escuela."""
        res = (
            supabase.table("classroom")
            .select("id")
            .eq("school_id", school_id)
            .eq("is_deleted", False)
            .execute()
        )
        return [c["id"] for c in res.data] if res.data else []

    def _get_school_doctor_ids(self, school_id: int) -> list[int]:
        """Retorna los doc_ids de los doctores asignados a la escuela."""
        res = (
            supabase.table("doctor_to_school")
            .select("doctor_id")
            .eq("school_id", school_id)
            .execute()
        )
        return [d["doctor_id"] for d in res.data] if res.data else []

    def _base_event_filter(self):
        """Condiciones base: no cancelado y no eliminado."""
        return {"is_canceled": False, "is_deleted": False}

    def _validate_event_ownership(self, event_id: int, sch_admin_id: int) -> dict:
        """Verifica que el evento existe, no está cancelado ni eliminado,
        y que fue creado por un admin de la misma escuela.
        Retorna el registro del evento."""
        event_res = (
            supabase.table("event")
            .select("*")
            .eq("id", event_id)
            .eq("is_canceled", False)
            .eq("is_deleted", False)
            .execute()
        )
        if not event_res.data:
            raise HTTPException(
                status_code=404,
                detail=f"No existe un evento activo con ID {event_id}."
            )
        event = event_res.data[0]

        # Verificar que al menos una participación del evento pertenece al admin
        participation_res = (
            supabase.table("event_participation")
            .select("id")
            .eq("id_event", event_id)
            .eq("id_school_admin", sch_admin_id)
            .eq("is_deleted", False)
            .limit(1)
            .execute()
        )
        if not participation_res.data:
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para acceder a este evento."
            )
        return event

    # ──────────────────────────────────────────────────────────
    # POST - Crear Evento
    # ──────────────────────────────────────────────────────────

    def create_event(self, user_id: int, payload) -> dict:
        admin = self._get_admin_record(user_id)
        sch_admin_id = admin["sch_admin_id"]
        school_id = admin["school_id"]

        # Validar que los classrooms pertenecen a la escuela
        valid_classroom_ids = self._get_school_classroom_ids(school_id)
        for cid in payload.classroom_ids:
            if cid not in valid_classroom_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"El salón con ID {cid} no pertenece a tu escuela."
                )

        # Validar que los doctores están asignados a la escuela
        valid_doctor_ids = self._get_school_doctor_ids(school_id)
        for did in payload.doctor_ids:
            if did not in valid_doctor_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"El doctor con ID {did} no está asignado a tu escuela."
                )

        # 1. Insertar el evento
        event_data = {
            "title": payload.title,
            "description": payload.description,
            "init_time": payload.init_time.isoformat(),
            "ent_time": payload.ent_time.isoformat(),
        }
        event_res = supabase.table("event").insert(event_data).execute()
        if not event_res.data:
            raise HTTPException(status_code=500, detail="Error al crear el evento.")
        event_id = event_res.data[0]["id"]

        # 2. Crear participaciones para cada classroom
        participation_rows = []
        for cid in payload.classroom_ids:
            participation_rows.append({
                "id_event": event_id,
                "id_classroom": cid,
                "id_school_admin": sch_admin_id,
            })

        # 3. Crear participaciones para cada doctor
        for did in payload.doctor_ids:
            participation_rows.append({
                "id_event": event_id,
                "id_doctor": did,
                "id_school_admin": sch_admin_id,
            })

        supabase.table("event_participation").insert(participation_rows).execute()

        return {
            "event_id": event_id,
            "title": payload.title,
            "classrooms_linked": len(payload.classroom_ids),
            "doctors_linked": len(payload.doctor_ids),
        }

    # ──────────────────────────────────────────────────────────
    # GET - Consultar Eventos (Paginación normal)
    # ──────────────────────────────────────────────────────────

    def get_events(self, user_id: int, page: int, size: int) -> dict:
        admin = self._get_admin_record(user_id)
        sch_admin_id = admin["sch_admin_id"]

        # Obtener los IDs de eventos donde participa este admin
        part_res = (
            supabase.table("event_participation")
            .select("id_event")
            .eq("id_school_admin", sch_admin_id)
            .eq("is_deleted", False)
            .execute()
        )
        if not part_res.data:
            return {"data": [], "total": 0, "page": page, "size": size}

        event_ids = list({p["id_event"] for p in part_res.data})

        # Contar total de eventos activos
        count_res = (
            supabase.table("event")
            .select("id", count="exact")
            .in_("id", event_ids)
            .eq("is_canceled", False)
            .eq("is_deleted", False)
            .execute()
        )
        total = count_res.count or 0
        if total == 0:
            return {"data": [], "total": 0, "page": page, "size": size}

        # Paginación
        offset = (page - 1) * size
        events_res = (
            supabase.table("event")
            .select("id, title, description, init_time, ent_time, created_at")
            .in_("id", event_ids)
            .eq("is_canceled", False)
            .eq("is_deleted", False)
            .order("init_time", desc=True)
            .range(offset, offset + size - 1)
            .execute()
        )

        return {
            "data": events_res.data,
            "total": total,
            "page": page,
            "size": size,
        }

    # ──────────────────────────────────────────────────────────
    # GET - Consultar Eventos por Fecha (Paginación por mes)
    # ──────────────────────────────────────────────────────────

    def get_events_by_month(self, user_id: int, year: int, month: int) -> dict:
        admin = self._get_admin_record(user_id)
        sch_admin_id = admin["sch_admin_id"]

        # Calcular rango del mes
        _, last_day = monthrange(year, month)
        start_date = f"{year}-{month:02d}-01T00:00:00+00:00"
        end_date = f"{year}-{month:02d}-{last_day}T23:59:59+00:00"

        # Obtener IDs de eventos del admin
        part_res = (
            supabase.table("event_participation")
            .select("id_event")
            .eq("id_school_admin", sch_admin_id)
            .eq("is_deleted", False)
            .execute()
        )
        if not part_res.data:
            return {"data": [], "year": year, "month": month, "total": 0}

        event_ids = list({p["id_event"] for p in part_res.data})

        # Filtrar eventos por rango de fechas
        events_res = (
            supabase.table("event")
            .select("id, title, description, init_time, ent_time, created_at")
            .in_("id", event_ids)
            .eq("is_canceled", False)
            .eq("is_deleted", False)
            .gte("init_time", start_date)
            .lte("init_time", end_date)
            .order("init_time", desc=False)
            .execute()
        )

        return {
            "data": events_res.data if events_res.data else [],
            "year": year,
            "month": month,
            "total": len(events_res.data) if events_res.data else 0,
        }

    # ──────────────────────────────────────────────────────────
    # GET - Detalle de un Evento
    # ──────────────────────────────────────────────────────────

    def get_event_detail(self, user_id: int, event_id: int) -> dict:
        admin = self._get_admin_record(user_id)
        sch_admin_id = admin["sch_admin_id"]

        event = self._validate_event_ownership(event_id, sch_admin_id)

        # Obtener participaciones del evento
        parts_res = (
            supabase.table("event_participation")
            .select("id_classroom, id_doctor, id_school_admin")
            .eq("id_event", event_id)
            .eq("is_deleted", False)
            .execute()
        )

        classroom_ids = list({p["id_classroom"] for p in parts_res.data if p.get("id_classroom")})
        doctor_ids = list({p["id_doctor"] for p in parts_res.data if p.get("id_doctor")})
        admin_ids = list({p["id_school_admin"] for p in parts_res.data if p.get("id_school_admin")})

        # Obtener info de salones
        classrooms_info = []
        if classroom_ids:
            cr_res = (
                supabase.table("classroom")
                .select("id, category, level, section")
                .in_("id", classroom_ids)
                .execute()
            )
            classrooms_info = [
                {
                    "id": c["id"],
                    "label": f"{c.get('category', '')} {c.get('level', '')} {c.get('section', '')}".strip()
                }
                for c in cr_res.data
            ] if cr_res.data else []

        # Obtener info de doctores
        doctors_info = []
        if doctor_ids:
            docs_res = (
                supabase.table("doctor")
                .select("doc_id, user_id, especially")
                .in_("doc_id", doctor_ids)
                .execute()
            )
            if docs_res.data:
                doc_user_ids = [d["user_id"] for d in docs_res.data if d.get("user_id")]
                users_res = (
                    supabase.table("user")
                    .select("id, name, lastname, gender")
                    .in_("id", doc_user_ids)
                    .execute()
                )
                users_map = {u["id"]: u for u in users_res.data} if users_res.data else {}

                for doc in docs_res.data:
                    user = users_map.get(doc.get("user_id"), {})
                    gender = user.get("gender", "")
                    prefix = "Dra." if str(gender).strip().upper() in ["F", "FEMALE", "FEMENINO", "MUJER"] else "Dr."
                    full_name = f"{prefix} {user.get('name', '')} {user.get('lastname', '')}".strip()
                    doctors_info.append({
                        "doc_id": doc["doc_id"],
                        "name": full_name,
                        "specialty": doc.get("especially"),
                    })

        # Obtener info del admin creador
        admin_info = None
        if admin_ids:
            # Usamos el primer admin registrado como creador
            creator_id = admin_ids[0]
            admin_res = (
                supabase.table("school_administrator")
                .select("sch_admin_id, user_id, administrative_position")
                .eq("sch_admin_id", creator_id)
                .execute()
            )
            if admin_res.data:
                admin_user_id = admin_res.data[0].get("user_id")
                user_res = (
                    supabase.table("user")
                    .select("id, name, lastname, email")
                    .eq("id", admin_user_id)
                    .execute()
                )
                if user_res.data:
                    u = user_res.data[0]
                    admin_info = {
                        "sch_admin_id": creator_id,
                        "name": f"{u.get('name', '')} {u.get('lastname', '')}".strip(),
                        "email": u.get("email"),
                        "position": admin_res.data[0].get("administrative_position"),
                    }

        return {
            "event": {
                "id": event["id"],
                "title": event["title"],
                "description": event.get("description"),
                "init_time": event["init_time"],
                "ent_time": event["ent_time"],
                "created_at": event.get("created_at"),
            },
            "classrooms": classrooms_info,
            "doctors": doctors_info,
            "created_by": admin_info,
        }

    # ──────────────────────────────────────────────────────────
    # PATCH - Cancelar Evento
    # ──────────────────────────────────────────────────────────

    def cancel_event(self, user_id: int, event_id: int) -> dict:
        admin = self._get_admin_record(user_id)
        sch_admin_id = admin["sch_admin_id"]

        self._validate_event_ownership(event_id, sch_admin_id)

        # Cancelar el evento
        supabase.table("event").update({
            "is_canceled": True,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", event_id).execute()

        # Cancelar las participaciones asociadas
        supabase.table("event_participation").update({
            "is_canceled": True,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id_event", event_id).execute()

        return {"event_id": event_id, "status": "canceled"}

    # ──────────────────────────────────────────────────────────
    # PUT - Modificar datos base del Evento
    # ──────────────────────────────────────────────────────────

    def update_event(self, user_id: int, event_id: int, payload: dict) -> dict:
        admin = self._get_admin_record(user_id)
        sch_admin_id = admin["sch_admin_id"]

        event = self._validate_event_ownership(event_id, sch_admin_id)

        # Construir campos a actualizar (solo los que se enviaron)
        update_data = {}
        allowed_fields = ["title", "description", "init_time", "ent_time"]
        for field in allowed_fields:
            if field in payload and payload[field] is not None:
                value = payload[field]
                # Convertir datetimes a ISO string
                if isinstance(value, datetime):
                    value = value.isoformat()
                update_data[field] = value

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No se proporcionaron campos válidos para actualizar."
            )

        # Validar que ent_time > init_time si se modifican las fechas
        new_init = update_data.get("init_time", event["init_time"])
        new_ent = update_data.get("ent_time", event["ent_time"])
        if new_ent <= new_init:
            raise HTTPException(
                status_code=400,
                detail="La fecha de finalización debe ser posterior a la de inicio."
            )

        update_data["updated_at"] = datetime.utcnow().isoformat()

        result = (
            supabase.table("event")
            .update(update_data)
            .eq("id", event_id)
            .execute()
        )

        return result.data[0] if result.data else {"event_id": event_id, "status": "updated"}


school_admin_event_service = SchoolAdminEventService()
