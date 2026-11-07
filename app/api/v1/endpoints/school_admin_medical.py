"""Salud escolar: médicos, casos médicos y métricas de la escuela del administrador."""

from datetime import date
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.api.deps import get_current_admin_escuela
from app.core.openapi_responses import TENANT_DETAIL_RESPONSES, TENANT_RESPONSES
from app.schemas.responses import APIResponse
from app.services.school_admin_service import school_admin_service

router = APIRouter()

# ──────────────────────────────────────────────────────────
# DOCTORES (Personal Médico)
# ──────────────────────────────────────────────────────────

@router.get("/doctors", response_model=APIResponse[dict],
    summary="Listar médicos de la escuela",
    description=(
        "Retorna de forma paginada los médicos asignados a la escuela. Por cada uno devuelve "
        "nombre completo con tratamiento (Dr./Dra.), nombre y apellido por separado, "
        "especialidad, número de licencia, estatus respecto a la escuela, año de inicio de "
        "carrera y años de experiencia calculados."
    ),
    responses=TENANT_RESPONSES,
)
def get_doctors(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Lista de forma paginada los médicos asignados a la escuela.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. El vínculo médico-escuela vive en 'doctor_to_school'.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_doctors(
        user_id=user_id,
        page=page,
        size=size
    )
    return APIResponse(data=result, message="Lista de doctores obtenida exitosamente")


@router.get("/doctors/{doctor_id}", response_model=APIResponse[dict],
    summary="Obtener detalle de un médico",
    description=(
        "Retorna los datos profesionales del médico (licencia, especialidad, experiencia y "
        "estatus en la escuela) junto con sus datos personales de usuario. Verifica que el "
        "médico esté vinculado a la escuela del administrador."
    ),
    responses=TENANT_DETAIL_RESPONSES,
)
def get_doctor_detail(
    doctor_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Devuelve el detalle completo de un médico de la escuela.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. El médico solo es visible si está vinculado a la escuela resuelta.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela. También 403 si el médico no está vinculado a esta escuela.
        HTTPException(404): Si no existe un médico con ese ID.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_doctor_detail(
        user_id=user_id,
        doctor_id=doctor_id
    )
    return APIResponse(data=result, message="Detalle del médico obtenido exitosamente")


@router.patch("/doctors/{doctor_id}/suspend", response_model=APIResponse[dict],
    summary="Suspender médico",
    description=(
        "Suspende las labores del médico en la escuela del administrador, poniendo el estatus "
        "de la relación 'doctor_to_school' en SUSPENDIDO. No afecta su vínculo con otras "
        "escuelas."
    ),
    responses=TENANT_DETAIL_RESPONSES,
)
def suspend_doctor(
    doctor_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Suspende a un médico en la escuela del administrador.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. Solo se altera la fila de 'doctor_to_school' correspondiente a esa
        escuela; el médico conserva su estatus en las demás.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela. También 403 si el médico no está vinculado a esta escuela.
        HTTPException(404): Si no existe un médico con ese ID.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.suspend_doctor(
        user_id=user_id,
        doctor_id=doctor_id
    )
    return APIResponse(data=result, message=result["message"])


@router.patch("/doctors/{doctor_id}/activate", response_model=APIResponse[dict],
    summary="Reactivar médico",
    description=(
        "Reactiva las labores del médico en la escuela del administrador, poniendo el estatus "
        "de la relación 'doctor_to_school' en ACTIVO."
    ),
    responses=TENANT_DETAIL_RESPONSES,
)
def reactivate_doctor(
    doctor_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Reactiva a un médico en la escuela del administrador.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. Solo se altera la fila de 'doctor_to_school' correspondiente a esa
        escuela.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela. También 403 si el médico no está vinculado a esta escuela.
        HTTPException(404): Si no existe un médico con ese ID.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.reactivate_doctor(
        user_id=user_id,
        doctor_id=doctor_id
    )
    return APIResponse(data=result, message=result["message"])


# ──────────────────────────────────────────────────────────
# CASOS MÉDICOS
# ──────────────────────────────────────────────────────────

@router.get("/medical-cases", response_model=APIResponse[dict],
    summary="Listar casos médicos",
    description=(
        "Retorna de forma paginada los casos médicos de los estudiantes de la escuela. Por "
        "cada caso devuelve id, estado ('activo' si no tiene fecha de cierre, 'resuelto' en "
        "caso contrario), fecha de inicio, nombre del estudiante, tipo de caso y "
        "sintomatología."
    ),
    responses=TENANT_RESPONSES,
)
def get_medical_cases(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    current_year_only: bool = Query(False, description="Si es true, devuelve solo casos del año académico vigente."),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Lista de forma paginada los casos médicos de la escuela.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. Los casos se alcanzan a través de los estudiantes inscritos en salones
        de esa escuela.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_medical_cases(
        user_id=user_id,
        page=page,
        size=size,
        current_year_only=current_year_only
    )
    return APIResponse(data=result, message="Casos médicos obtenidos exitosamente")


@router.get("/medical-cases/search", response_model=APIResponse[dict],
    summary="Buscar casos médicos",
    description=(
        "Búsqueda paginada de casos médicos de la escuela con filtros opcionales e "
        "independientes entre sí: estado, tipo de caso, rango de fechas de inicio y texto "
        "libre. Con 'search_by' el texto se restringe al estudiante o al caso; si se omite, "
        "busca en ambos."
    ),
    responses=TENANT_RESPONSES,
)
def search_medical_cases(
    status: Optional[str] = Query(
        None,
        description="Estado del caso: 'activo' o 'resuelto'. "
                    "Resuelto = end_date y final_diagnosis no nulos. "
                    "Si se omite, se devuelven todos los casos.",
    ),
    type_of_case: Optional[str] = Query(
        None,
        description="Tipo de caso: ALERGIA | LESION | ENFERMEDAD | EMERGENCIA. "
                    "Si se omite, se devuelven todos los tipos.",
    ),
    date_from: Optional[date] = Query(
        None,
        description="Fecha de inicio mínima (init_date >= date_from). Formato: YYYY-MM-DD.",
    ),
    date_to: Optional[date] = Query(
        None,
        description="Fecha de inicio máxima (init_date <= date_to). Formato: YYYY-MM-DD.",
    ),
    q: Optional[str] = Query(
        None,
        description="Término de búsqueda por texto. Busca en nombre del estudiante y detalles del caso.",
    ),
    search_by: Optional[str] = Query(
        None,
        description="Tipo de búsqueda de texto: 'student' (por estudiante) o 'case' (por caso). Si se omite y se provee q, busca en ambos.",
    ),
    page: int = Query(1, ge=1, description="Número de página (empieza en 1)."),
    size: int = Query(20, ge=1, le=100, description="Elementos por página (máximo 100)."),
    current_year_only: bool = Query(False, description="Si es true, devuelve solo casos del año académico vigente."),
    admin_payload: dict = Depends(get_current_admin_escuela),
):
    """Busca casos médicos de la escuela aplicando filtros opcionales.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. Los casos se alcanzan a través de los estudiantes inscritos en salones
        de esa escuela.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.search_medical_cases(
        user_id=user_id,
        page=page,
        size=size,
        status=status,
        type_of_case=type_of_case,
        date_from=date_from,
        date_to=date_to,
        q=q,
        search_by=search_by,
        current_year_only=current_year_only,
    )
    return APIResponse(data=result, message="Búsqueda de casos médicos completada exitosamente")


@router.get("/students/medical-cases/tendency", response_model=APIResponse[dict],
    summary="Tendencia de casos médicos",
    description=(
        "Serie temporal de nuevos casos médicos de la escuela, agrupada por mes o por semana "
        "según 'mode'. Incluye el total de incidentes, la tasa de crecimiento respecto al "
        "período anterior y una recta de tendencia para graficar."
    ),
    responses=TENANT_RESPONSES,
)
def get_medical_cases_tendency(
    mode: str = Query("monthly", description="Modo de agrupación: 'monthly' o 'weekly'"),
    months: int = Query(3, ge=1, le=24, description="Meses hacia atrás a analizar (modo monthly)"),
    weeks: int = Query(12, ge=1, le=52, description="Semanas hacia atrás a analizar (modo weekly)"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Calcula la tendencia de nuevos casos médicos de la escuela.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. La serie se construye solo con los estudiantes de esa escuela.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_medical_cases_tendency(
        user_id=user_id,
        mode=mode,
        months=months,
        weeks=weeks,
    )
    return APIResponse(data=result, message="Tendencia de casos médicos obtenida exitosamente")


@router.get("/medical-cases/{case_id}", response_model=APIResponse[dict],
    summary="Obtener detalle de un caso médico",
    description=(
        "Retorna el caso médico con todo su contexto: datos del caso, del estudiante "
        "afectado, del médico tratante, de sus representantes y su información de salud."
    ),
    responses=TENANT_DETAIL_RESPONSES,
)
def get_medical_case_detail(
    case_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Devuelve el detalle de un caso médico con todo su contexto.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. El caso solo es visible si su estudiante pertenece a esa escuela.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela. También 403 si el estudiante del caso pertenece a otra escuela.
        HTTPException(404): Si no existe un caso médico activo con ese ID.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_medical_case_detail(
        user_id=user_id,
        case_id=case_id
    )
    return APIResponse(data=result, message="Detalle del caso médico obtenido exitosamente")




@router.get("/students/{student_id}/metrics", response_model=APIResponse[dict],
    summary="Historial de métricas de un estudiante",
    description=(
        "Retorna las series de peso y estatura de un estudiante, de la medición más reciente "
        "hacia atrás. Si el estudiante no tiene mediciones, 'data' viene en null y el mensaje "
        "lo indica."
    ),
    responses=TENANT_DETAIL_RESPONSES,
)
def get_student_metrics_history(
    student_id: int,
    limit: int = Query(15, ge=1, le=200, description="Cantidad de registros a traer (más recientes primero)."),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Devuelve el histórico de peso y estatura de un estudiante.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. El estudiante debe estar inscrito en un salón de esa escuela.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela. También 403 si el estudiante no está inscrito en ningún salón o
            pertenece a otra escuela.
        HTTPException(404): Si no existe un estudiante activo con ese ID.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_student_metrics_history(
        user_id=user_id,
        student_id=student_id,
        limit=limit
    )
    message = "Historial de métricas obtenido exitosamente" if result else "El estudiante no tiene métricas registradas."
    return APIResponse(data=result, message=message)
