from datetime import date
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.api.deps import get_current_admin_escuela
from app.schemas.responses import APIResponse
from app.services.school_admin_service import school_admin_service

router = APIRouter()

# ──────────────────────────────────────────────────────────
# DOCTORES (Personal Médico)
# ──────────────────────────────────────────────────────────

@router.get("/doctors", response_model=APIResponse[dict])
def get_doctors(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Lista paginada de los médicos (doctores) asociados a la escuela.
    
    Campos devueltos por doctor:
    - fullname (nombre y apellido concatenado, prefijado con Dr. o Dra. según género)
    - name (nombre del médico)
    - lastname (apellido del médico)
    - specialty (especialidad médica)
    - medical_license (número de licencia médica)
    - status (estado del médico respecto a la escuela, ej. Activo/Inactivo)
    - experience_years (año de inicio de carrera)
    - years_of_experience (años calculados de experiencia)
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_doctors(
        user_id=user_id,
        page=page,
        size=size
    )
    return APIResponse(data=result, message="Lista de doctores obtenida exitosamente")


@router.get("/doctors/{doctor_id}", response_model=APIResponse[dict])
def get_doctor_detail(
    doctor_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Retorna el detalle completo de un médico (doctor) para el administrador de escuela.
    
    Incluye:
    - **doctor_info**: Datos profesionales (licencia, especialidad, experiencia, estatus en la escuela).
    - **user_info**: Datos personales del usuario (nombre, correo, dirección, teléfonos, biografía, etc.).
    
    Verifica que el médico esté vinculado a la escuela del administrador.
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_doctor_detail(
        user_id=user_id,
        doctor_id=doctor_id
    )
    return APIResponse(data=result, message="Detalle del médico obtenido exitosamente")


@router.patch("/doctors/{doctor_id}/suspend", response_model=APIResponse[dict])
def suspend_doctor(
    doctor_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Suspende las labores de un médico (doctor) en la escuela del administrador.
    Cambia el estatus de la relación a 'SUSPENDIDO'.
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.suspend_doctor(
        user_id=user_id,
        doctor_id=doctor_id
    )
    return APIResponse(data=result, message=result["message"])


@router.patch("/doctors/{doctor_id}/activate", response_model=APIResponse[dict])
def reactivate_doctor(
    doctor_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Activa o reactiva las labores de un médico (doctor) en la escuela del administrador.
    Cambia el estatus de la relación a 'ACTIVO'.
    
    Requiere JWT (admin_escuela).
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

@router.get("/medical-cases", response_model=APIResponse[dict])
def get_medical_cases(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    current_year_only: bool = Query(False, description="Si es true, devuelve solo casos del año académico vigente."),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Lista paginada de los casos médicos asociados a los estudiantes de la escuela.
    
    Campos devueltos por caso:
    - id
    - status ('activo' si end_date es nulo, 'resuelto' caso contrario)
    - start_date (fecha de inicio)
    - student_name (nombre y apellido concatenado)
    - type_of_case
    - description (symptomatology)
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_medical_cases(
        user_id=user_id,
        page=page,
        size=size,
        current_year_only=current_year_only
    )
    return APIResponse(data=result, message="Casos médicos obtenidos exitosamente")


@router.get("/medical-cases/search", response_model=APIResponse[dict])
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
    """
    Búsqueda paginada de casos médicos de la escuela con filtros opcionales e independientes.
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


@router.get("/students/medical-cases/tendency", response_model=APIResponse[dict])
def get_medical_cases_tendency(
    mode: str = Query("monthly", description="Modo de agrupación: 'monthly' o 'weekly'"),
    months: int = Query(3, ge=1, le=24, description="Meses hacia atrás a analizar (modo monthly)"),
    weeks: int = Query(12, ge=1, le=52, description="Semanas hacia atrás a analizar (modo weekly)"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Tendencia de nuevos casos médicos en el tiempo para los estudiantes de la escuela.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_medical_cases_tendency(
        user_id=user_id,
        mode=mode,
        months=months,
        weeks=weeks,
    )
    return APIResponse(data=result, message="Tendencia de casos médicos obtenida exitosamente")


@router.get("/medical-cases/{case_id}", response_model=APIResponse[dict])
def get_medical_case_detail(
    case_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Retorna el detalle completo de un caso médico junto con los datos del estudiante 
    involucrado y de sus representantes (padres).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_medical_case_detail(
        user_id=user_id,
        case_id=case_id
    )
    return APIResponse(data=result, message="Detalle del caso médico obtenido exitosamente")




@router.get("/students/{student_id}/metrics", response_model=APIResponse[dict])
def get_student_metrics_history(
    student_id: int,
    limit: int = Query(15, ge=1, le=200, description="Cantidad de registros a traer (más recientes primero)."),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Historial de métricas corporales de un estudiante.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_student_metrics_history(
        user_id=user_id,
        student_id=student_id,
        limit=limit
    )
    message = "Historial de métricas obtenido exitosamente" if result else "El estudiante no tiene métricas registradas."
    return APIResponse(data=result, message=message)
