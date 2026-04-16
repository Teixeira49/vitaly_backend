from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_admin_escuela
from app.schemas.responses import APIResponse
from app.schemas.event import EventCreate, EventUpdate
from app.services.school_admin_event_service import school_admin_event_service

router = APIRouter()


# ──────────────────────────────────────────────────────────
# POST - Crear Evento
# ──────────────────────────────────────────────────────────

@router.post("/", response_model=APIResponse[dict])
def create_event(
    payload: EventCreate,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Crea un nuevo evento vinculado a la escuela del administrador autenticado.

    Requiere:
    - **title**: Nombre del evento.
    - **init_time** / **ent_time**: Fechas de inicio y fin (ISO 8601).
    - **classroom_ids**: Lista de IDs de salones participantes.
    - **doctor_ids**: Lista de IDs de doctores participantes.

    Se generan registros individuales en `event_participation` por cada
    salón y doctor involucrado, vinculados al admin creador.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_event_service.create_event(user_id=user_id, payload=payload)
    return APIResponse(data=result, message="Evento creado exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Consultar Eventos (Paginación normal)
# ──────────────────────────────────────────────────────────

@router.get("/", response_model=APIResponse[dict])
def get_events(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Lista paginada de eventos activos (no cancelados, no eliminados)
    vinculados a la escuela del administrador autenticado.

    Los resultados se ordenan por fecha de inicio (más reciente primero).

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_event_service.get_events(user_id=user_id, page=page, size=size)
    return APIResponse(data=result, message="Eventos obtenidos exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Consultar Eventos por Mes (Paginación por fecha)
# ──────────────────────────────────────────────────────────

@router.get("/by-month", response_model=APIResponse[dict])
def get_events_by_month(
    year: int = Query(..., ge=2020, le=2100, description="Año a consultar"),
    month: int = Query(..., ge=1, le=12, description="Mes a consultar (1-12)"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Retorna todos los eventos activos del mes indicado, ordenados cronológicamente.

    A diferencia del listado paginado normal, este endpoint filtra por rango de fechas
    (primer día del mes hasta el último día del mes) en lugar de usar paginación offset.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_event_service.get_events_by_month(user_id=user_id, year=year, month=month)
    return APIResponse(data=result, message="Eventos del mes obtenidos exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Detalle de un Evento
# ──────────────────────────────────────────────────────────

@router.get("/{event_id}", response_model=APIResponse[dict])
def get_event_detail(
    event_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Retorna el detalle completo de un evento específico.

    Incluye:
    - **event**: Datos del evento (título, descripción, fechas).
    - **classrooms**: Lista de salones vinculados (grado, nivel, sección).
    - **doctors**: Lista de doctores vinculados (nombre, especialidad).
    - **created_by**: Información del administrador que creó el evento.

    Solo se muestran eventos activos (no cancelados, no eliminados)
    que pertenezcan a la escuela del admin autenticado.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_event_service.get_event_detail(user_id=user_id, event_id=event_id)
    return APIResponse(data=result, message="Detalle del evento obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# PATCH - Cancelar Evento
# ──────────────────────────────────────────────────────────

@router.patch("/{event_id}/cancel", response_model=APIResponse[dict])
def cancel_event(
    event_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Cancela un evento activo. Establece `is_canceled = True` tanto en el evento
    como en todas sus participaciones asociadas.

    Un evento cancelado dejará de ser visible en todos los endpoints de consulta.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_event_service.cancel_event(user_id=user_id, event_id=event_id)
    return APIResponse(data=result, message="Evento cancelado exitosamente")


# ──────────────────────────────────────────────────────────
# PUT - Modificar datos base del Evento
# ──────────────────────────────────────────────────────────

@router.put("/{event_id}", response_model=APIResponse[dict])
def update_event(
    event_id: int,
    payload: EventUpdate,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Modifica los datos base de un evento (título, descripción, fechas).

    **No** modifica las participaciones (salones y doctores vinculados).
    Solo se pueden editar campos enviados; los omitidos conservan su valor actual.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_event_service.update_event(
        user_id=user_id,
        event_id=event_id,
        payload=payload.model_dump(exclude_unset=True)
    )
    return APIResponse(data=result, message="Evento actualizado exitosamente")
