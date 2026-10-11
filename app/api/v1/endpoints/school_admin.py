from fastapi import APIRouter, Depends, Query, UploadFile, File

from app.api.deps import get_current_admin_escuela
from app.schemas.responses import APIResponse
from app.schemas.user import UserUpdate, UserPhotoResponse
from app.services.school_admin_service import school_admin_service
from app.services import profile_photo_service

router = APIRouter()


# ──────────────────────────────────────────────────────────
# Profile - Mi Perfil de Administrador
# ──────────────────────────────────────────────────────────

@router.get("/profile", response_model=APIResponse[dict])
def get_my_profile(
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Retorna el perfil del administrador de escuela autenticado.
    
    Incluye la información del usuario, la información del administrador 
    y datos básicos de la escuela a la que pertenece (nombre, año de fundación y dirección).
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_my_profile(user_id=user_id)
    return APIResponse(data=result, message="Perfil obtenido exitosamente")


@router.put("/profile", response_model=APIResponse[dict])
def update_my_profile(
    payload: UserUpdate,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Actualiza la información personal del administrador de escuela autenticado.
    
    Permite modificar: nombre, apellido, cédula (identity_number), 
    fecha de nacimiento (birthday), género, dirección y biografía.
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.update_my_profile(
        user_id=user_id,
        payload=payload.model_dump(exclude_unset=True)
    )
    return APIResponse(data=result, message="Perfil actualizado exitosamente")


@router.post(
    "/profile/photo",
    response_model=APIResponse[UserPhotoResponse],
    summary="Subir foto de perfil",
    description="Sube una imagen al bucket de ImageKit.io y actualiza la URL en el perfil del usuario autenticado."
)
def upload_my_profile_photo(
    file: UploadFile = File(..., description="Archivo de imagen (JPEG, PNG o WebP, máx. 5MB)"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Sube y actualiza la foto de perfil del administrador de escuela autenticado.

    Multi-tenancy:
        El usuario afectado se deriva exclusivamente del token JWT (admin_payload['sub']).
        No acepta ni confía en identificadores enviados en el cuerpo.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(400): Si el archivo no es una imagen válida (JPEG, PNG, WebP) o excede 5MB.
        HTTPException(500): Si el servicio ImageKit no está configurado en el servidor.
        HTTPException(502): Si la subida a ImageKit falla por error de pasarela.
    """
    user_id = int(admin_payload["sub"])
    # Plain `def` endpoint: FastAPI runs it in the threadpool, so the blocking
    # ImageKit/Supabase calls never block the event loop.
    file_bytes = profile_photo_service.read_upload_capped(file.file)
    result = school_admin_service.upload_my_profile_photo(
        user_id=user_id,
        file_bytes=file_bytes,
        content_type=file.content_type or ""
    )
    return APIResponse(
        success=True,
        data=UserPhotoResponse(**result),
        message="Foto de perfil subida y actualizada exitosamente"
    )


@router.delete(
    "/profile/photo",
    response_model=APIResponse[UserPhotoResponse],
    summary="Eliminar foto de perfil",
    description="Elimina la foto de perfil del administrador autenticado, estableciendo photo_url en null."
)
def delete_my_profile_photo(
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Elimina la foto de perfil del administrador de escuela autenticado.

    Multi-tenancy:
        El usuario afectado se deriva exclusivamente del token JWT (admin_payload['sub']).
        No acepta ni confía en identificadores enviados en el cuerpo.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(400): Si no se pudo actualizar el registro en la base de datos.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.delete_my_profile_photo(user_id=user_id)
    return APIResponse(
        success=True,
        data=UserPhotoResponse(**result),
        message="Foto de perfil eliminada exitosamente"
    )



# ──────────────────────────────────────────────────────────
# GET - Resumen / Métricas de Estudiantes
# ──────────────────────────────────────────────────────────

@router.get("/students/resume", response_model=APIResponse[dict])
def get_students_resume(
    category: int = Query(None, description="ID de la categoría del aula (ej. 1=PREESCOLAR). Filtra el resumen por categoría."),
    grade: int = Query(None, description="Nivel/grado del aula. Requiere 'category'."),
    section: str = Query(None, description="Letra de la sección (ej. 'A'). Requiere 'category' y 'grade'."),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Resumen métrico de los estudiantes pertenecientes a la escuela del admin autenticado,
    correspondientes al año académico vigente.

    **Filtros opcionales (jerárquicos):**
    - **category**: Filtra por categoría de aula (classroom_category). Ej: 1=PREESCOLAR.
    - **grade**: Filtra por nivel/grado. *Requiere `category`.*
    - **section**: Filtra por sección (letra). *Requiere `category` y `grade`.*

    **Métricas:**
    - `total_students`: Número total de estudiantes en el alcance seleccionado.
    - `overweight_students`: Estudiantes con BMI > 24.9.
    - `malnourished_students`: Estudiantes con BMI < 18.5.
    - `active_cases`: Casos médicos activos (sin fecha de cierre ni diagnóstico final).
    - `optimal_students`: total_students - overweight - malnourished.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_students_resume(
        user_id=user_id,
        category=category,
        grade=grade,
        section=section,
    )
    return APIResponse(data=result, message="Resumen de estudiantes obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Historial Médico de un Estudiante
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
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_student_medical_history(
        user_id=user_id,
        student_id=student_id,
        page=page,
        size=size
    )
    return APIResponse(data=result, message="Historial médico obtenido exitosamente")
