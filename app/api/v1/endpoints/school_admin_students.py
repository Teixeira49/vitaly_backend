from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_admin_escuela
from app.schemas.responses import APIResponse
from app.schemas.student import StudentUpdateSchoolAdmin
from app.services.school_admin_service import school_admin_service

router = APIRouter()








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
# PUT - Actualizar perfil del estudiante (incluyendo representante)
# ──────────────────────────────────────────────────────────

@router.put("/students/{student_id}", response_model=APIResponse[dict])
def update_student_profile(
    student_id: int,
    payload: StudentUpdateSchoolAdmin,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Actualiza el perfil de un estudiante. Los campos opcionales permitidos son:
    - name
    - lastname
    - identity_number
    - gender
    - blood_type
    - birthday
    - representative_id (Reemplaza al padre actual en la tabla student_representative)
    
    Verifica de antemano que el estudiante se encuentre validado en un salón
    perteneciente a la escuela administrada por el usuario en sesión.
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.update_student_profile(
        user_id=user_id,
        student_id=student_id,
        payload=payload.model_dump(exclude_unset=True)
    )
    return APIResponse(data=result, message="Perfil del estudiante y representante actualizados exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Búsqueda global de Representantes (Paginado)
# ──────────────────────────────────────────────────────────

@router.get("/search/representatives", response_model=APIResponse[dict])
def search_representatives(
    query: str = Query(..., min_length=1, description="Nombre o Apellido del representante"),
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Buscador global de representantes basado en coincidencias parciales ILIKE de nombre o apellido.
    
    Usado principalmente para ubicar rápidamente el ID de un representante y re-asignarlo empleando 
    la edición de perfil estudiantil.
    
    Campos devueltos por representante:
    - email
    - name
    - lastname
    - representative_id (el necesario para update)
    - user_id
    - ocupation
    
    Requiere JWT (admin_escuela).
    """
    result = school_admin_service.search_representatives(
        query=query,
        page=page,
        size=size
    )
    return APIResponse(data=result, message="Búsqueda completada exitosamente")


# ──────────────────────────────────────────────────────────
# PATCH - Activar Estudiante
# ──────────────────────────────────────────────────────────

@router.patch("/students/{student_id}/activate", response_model=APIResponse[dict])
def activate_student(
    student_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Activa a un estudiante previamente desactivado.
    
    Verifica de antemano que el estudiante se encuentre validado en un salón
    perteneciente a la escuela administrada por el usuario en sesión.
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.activate_student(
        user_id=user_id,
        student_id=student_id
    )
    return APIResponse(data=result, message="Estudiante activado exitosamente")


# ──────────────────────────────────────────────────────────
# PATCH - Desactivar Estudiante
# ──────────────────────────────────────────────────────────

@router.patch("/students/{student_id}/deactivate", response_model=APIResponse[dict])
def deactivate_student(
    student_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Desactiva a un estudiante activo.
    
    Verifica de antemano que el estudiante se encuentre validado en un salón
    perteneciente a la escuela administrada por el usuario en sesión.
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.deactivate_student(
        user_id=user_id,
        student_id=student_id
    )
    return APIResponse(data=result, message="Estudiante desactivado exitosamente")



