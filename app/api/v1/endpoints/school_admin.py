from fastapi import APIRouter, Depends, Query
from typing import List

from app.api.deps import get_current_admin_escuela
from app.schemas.responses import APIResponse
from app.services.school_admin_service import school_admin_service

router = APIRouter()


# ──────────────────────────────────────────────────────────
# GET - Resumen / Métricas de Estudiantes
# ──────────────────────────────────────────────────────────

@router.get("/students/resume", response_model=APIResponse[dict])
def get_students_resume(
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Resumen métrico de los estudiantes pertenecientes a la escuela del admin autenticado.

    Métricas:
    - **total_students**: Número total de estudiantes vinculados a la escuela.
    - **overweight_students**: (Hardcodeado a 0) Estudiantes con sobrepeso.
    - **malnourished_students**: (Hardcodeado a 0) Estudiantes con desnutrición.
    - **active_cases**: (Hardcodeado a 0) Casos médicos activos.
    - **optimal_students**: total_students - overweight - malnourished.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_students_resume(user_id=user_id)
    return APIResponse(data=result, message="Resumen de estudiantes obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Grados Académicos (Classrooms del año vigente)
# ──────────────────────────────────────────────────────────

@router.get("/classrooms", response_model=APIResponse[dict])
def get_academic_grades(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Lista paginada de grados/salones de la escuela del admin, filtrados por el año académico vigente (is_current=True).
    Los resultados se ordenan por categoría y luego por nivel.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_academic_grades(user_id=user_id, page=page, size=size)
    return APIResponse(data=result, message="Grados académicos obtenidos exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Estudiantes de un salón específico
# ──────────────────────────────────────────────────────────

@router.get("/classrooms/{classroom_id}/students", response_model=APIResponse[dict])
def get_students_by_classroom(
    classroom_id: int,
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Lista paginada de los estudiantes inscritos en un salón específico.
    Valida que el salón pertenezca a la misma escuela del admin autenticado.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_students_by_classroom(
        user_id=user_id,
        classroom_id=classroom_id,
        page=page,
        size=size
    )
    return APIResponse(data=result, message="Estudiantes del salón obtenidos exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Detalle completo de un estudiante
# ──────────────────────────────────────────────────────────

@router.get("/students/{student_id}", response_model=APIResponse[dict])
def get_student_detail(
    student_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Detalle completo de un estudiante para el administrador de escuela.

    Incluye:
    - **student**: Datos base del estudiante.
    - **representatives**: Lista de representantes vinculados (con sus datos de usuario), o `null` si no tiene ninguno.
    - **health_info**: Métricas de salud más recientes (peso, estatura, IMC, estado nutricional: `OPTIMO`, `OBESO`, `DESNUTRIDO`), o `null` si no hay registros.

    Restringe el acceso sólo a estudiantes pertenecientes a la misma escuela del admin autenticado.
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_student_detail(user_id=user_id, student_id=student_id)
    return APIResponse(data=result, message="Detalle del estudiante obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Historial de métricas (peso/altura) de un estudiante
# ──────────────────────────────────────────────────────────

@router.get("/students/{student_id}/metrics", response_model=APIResponse[dict])
def get_student_metrics_history(
    student_id: int,
    limit: int = Query(15, ge=1, le=200, description="Cantidad de registros a traer (más recientes primero). Por defecto: 15."),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Historial de métricas corporales de un estudiante.

    Retorna las últimas `limit` mediciones (por defecto 15) ordenadas de más reciente a más antigua,
    separadas por tipo:

    ```json
    {
      "peso":   [{"fecha": "...", "valor": 45.2}, ...],
      "altura": [{"fecha": "...", "valor": 1.52}, ...]
    }
    ```

    Si no hay métricas registradas, retorna `data: null` con status `200`.
    Restringe el acceso sólo a estudiantes pertenecientes a la misma escuela del admin autenticado.
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_student_metrics_history(
        user_id=user_id,
        student_id=student_id,
        limit=limit
    )
    message = "Historial de métricas obtenido exitosamente" if result else "El estudiante no tiene métricas registradas."
    return APIResponse(data=result, message=message)


# ──────────────────────────────────────────────────────────
# GET - Casos médicos de los estudiantes (Paginado)
# ──────────────────────────────────────────────────────────

@router.get("/medical-cases", response_model=APIResponse[dict])
def get_medical_cases(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
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
        size=size
    )
    return APIResponse(data=result, message="Casos médicos obtenidos exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Detalle de un caso médico específico
# ──────────────────────────────────────────────────────────

@router.get("/medical-cases/{case_id}", response_model=APIResponse[dict])
def get_medical_case_detail(
    case_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Retorna el detalle completo de un caso médico junto con los datos del estudiante 
    involucrado y de sus representantes (padres).
    
    Verifica que el caso médico corresponda a un estudiante inscrito en una clase 
    perteneciente a la escuela del administrador.
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_medical_case_detail(
        user_id=user_id,
        case_id=case_id
    )
    return APIResponse(data=result, message="Detalle del caso médico obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Doctores de la escuela (Paginado)
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
    - name (nombre y apellido concatenado, prefijado con Dr. o Dra. según género)
    - specialty (especialidad médica)
    - medical_license (número de licencia médica)
    - status (estado del médico respecto a la escuela, ej. Activo/Inactivo)
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_doctors(
        user_id=user_id,
        page=page,
        size=size
    )
    return APIResponse(data=result, message="Lista de doctores obtenida exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Detalle de un Representante y sus Hijos
# ──────────────────────────────────────────────────────────

@router.get("/representatives/{parent_id}", response_model=APIResponse[dict])
def get_parent_detail(
    parent_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Lista el detalle de un representante junto con un conteo y lista de todos sus hijos asociados.
    
    Verifica que al menos uno de los estudiantes pertenezca a la escuela administrada por el token
    proporcionado, en caso contrario retorna error 403 de acceso denegado.
    
    Campos devueltos por hijo (children):
    - id
    - name (nombre y apellido concatenado)
    - birthday
    - current_grade (grado actual concatenado con el listado)
    - bmi_status (DESNUTRIDO, OPTIMO, OBESO, SIN DATOS)
    - has_active_medical_case (boolean)
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_parent_detail(
        user_id=user_id,
        parent_id=parent_id
    )
    return APIResponse(data=result, message="Detalle del representante obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Historial médico de un estudiante específico (Paginado)
# ──────────────────────────────────────────────────────────

@router.get("/students/{student_id}/medical-history", response_model=APIResponse[dict])
def get_student_medical_history(
    student_id: int,
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Lista paginada del historial médico (casos médicos) de un estudiante específico.
    
    Verifica que el estudiante pertenezca a la escuela administrada por el token
    proporcionado, en caso contrario retorna error 403 de acceso denegado.
    
    Campos devueltos por caso médico:
    - id
    - start_date (fecha de inicio)
    - type_of_case (tipo de caso)
    - is_active (boolean que indica si sigue activo determinando si end_date es nulo)
    - title
    - description (symptomatology)
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_student_medical_history(
        user_id=user_id,
        student_id=student_id,
        page=page,
        size=size
    )
    return APIResponse(data=result, message="Historial médico obtenido exitosamente")
