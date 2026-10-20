"""Gestión global de escuelas, salones y estudiantes por el administrador de sistema."""

from fastapi import APIRouter, Depends, Query
from typing import List
from app.api.deps import get_current_admin_sistema
from app.core.openapi_responses import BAD_REQUEST, PROTECTED_DETAIL_RESPONSES, PROTECTED_RESPONSES
from app.schemas.responses import APIResponse
from app.schemas.school import (
    SchoolCreate, ClassroomCreate,
    SchoolRead, PaginatedSchoolsResponse,
    ClassroomRead, PaginatedClassroomsResponse,
    StudentRead, PaginatedStudentsResponse,
)
from app.schemas.student import StudentCreate, StudentUpdate, ClassroomRegistrationCreate, BulkClassroomRegistrationCreate
from app.services.admin_service import admin_service

router = APIRouter()

@router.post("/", response_model=APIResponse[str],
    summary="Crear escuela",
    description=(
        "Registra una nueva institución. Valida que el año de fundación no sea negativo ni "
        "futuro, que el RIF sea único en todo el sistema y que no exista ya otra escuela con "
        "el mismo nombre dentro del mismo estado."
    ),
    responses={**PROTECTED_RESPONSES, **BAD_REQUEST},
)
def create_school(
    payload: SchoolCreate,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """Registra una nueva escuela en la plataforma.

    Multi-tenancy:
        Crea el tenant: es la única ruta que da de alta una escuela.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(400): Si el año de fundación es inválido, el RIF ya existe, o
            el par nombre+estado está duplicado.
        HTTPException(500): Si la inserción no devuelve la fila creada.
    """
    msg = admin_service.create_school(payload)
    return APIResponse(data=msg, message="Registro completado")

@router.post("/classrooms", response_model=APIResponse[str],
    summary="Crear salón de clase",
    description=(
        "Crea un salón dentro de una escuela y un año académico. El nivel debe caber en el "
        "rango de su categoría (Preescolar 1-3, Primaria 1-6, Bachillerato 1-5, configurable "
        "en Settings). La sección es opcional, admite hasta 3 caracteres alfanuméricos y se "
        "normaliza a mayúsculas."
    ),
    responses={**PROTECTED_DETAIL_RESPONSES, **BAD_REQUEST},
)
def create_classroom(
    payload: ClassroomCreate,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """Crea un salón para una escuela y un año académico concretos.

    Multi-tenancy:
        El 'school_id' llega por el cuerpo, lo cual solo es admisible aquí porque la
        ruta está tras el gate de admin_sistema, cuyo alcance es global.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(400): Si la categoría es desconocida, el nivel queda fuera de
            rango, o ya existe un salón idéntico.
        HTTPException(404): Si la escuela o el año académico no existen.
        HTTPException(500): Si la inserción no devuelve la fila creada.
    """
    msg = admin_service.create_classroom(payload)
    return APIResponse(data=msg, message="Salón registrado exitosamente")

@router.post("/students", response_model=APIResponse[str],
    summary="Crear estudiante",
    description=(
        "Registra un estudiante en la plataforma, sin inscribirlo todavía en un salón. La "
        "fecha de nacimiento no puede ser futura ni implicar más de 21 años; si se envía "
        "cédula, se valida que no pertenezca ya a otro estudiante activo."
    ),
    responses={**PROTECTED_RESPONSES, **BAD_REQUEST},
)
def create_student(
    payload: StudentCreate,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """Registra un nuevo estudiante en la plataforma.

    Multi-tenancy:
        El estudiante nace sin escuela; queda asociado a una al inscribirlo en un
        salón mediante /classrooms/register.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(400): Si la cédula ya pertenece a otro estudiante activo.
        HTTPException(500): Si la inserción no devuelve la fila creada.
    """
    msg = admin_service.create_student(payload)
    return APIResponse(data=msg, message="Estudiante registrado exitosamente")

@router.patch("/students/{student_id}", response_model=APIResponse[str],
    summary="Actualizar estudiante",
    description=(
        "Modifica únicamente los campos enviados en el cuerpo. 'is_active' e 'is_deleted' no "
        "son modificables por esta vía. Si se cambia la cédula, se valida que no pertenezca "
        "ya a otro estudiante activo."
    ),
    responses={**PROTECTED_DETAIL_RESPONSES, **BAD_REQUEST},
)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """Actualiza los atributos de un estudiante existente.

    Multi-tenancy:
        Alcance global: puede modificar estudiantes de cualquier escuela.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(404): Si el estudiante no existe.
        HTTPException(400): Si el estudiante está eliminado, si la nueva cédula ya
            pertenece a otro estudiante activo, o si no se envió ningún campo.
    """
    msg = admin_service.update_student(student_id=student_id, payload=payload)
    return APIResponse(data=msg, message="Estudiante actualizado exitosamente")

@router.post("/classrooms/register", response_model=APIResponse[str],
    summary="Inscribir estudiante en un salón",
    description=(
        "Vincula un estudiante a un salón dentro de un año académico. Verifica que el salón "
        "esté activo y pertenezca al año indicado, y que el estudiante no esté ya inscrito en "
        "él. El estatus por defecto es 2."
    ),
    responses={**PROTECTED_DETAIL_RESPONSES, **BAD_REQUEST},
)
def register_student_to_classroom(
    payload: ClassroomRegistrationCreate,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """Inscribe un estudiante en un salón de clase.

    Multi-tenancy:
        La inscripción es lo que ata al estudiante a una escuela, a través del salón.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(404): Si el salón no existe o está eliminado.
        HTTPException(400): Si el salón no pertenece al año académico indicado, o si
            el estudiante ya está inscrito en él.
        HTTPException(500): Si la inserción no devuelve la fila creada.
    """
    msg = admin_service.register_student_to_classroom(payload)
    return APIResponse(data=msg, message="Estudiante vinculado al salón exitosamente")

@router.post("/classrooms/register/bulk", response_model=APIResponse[str],
    summary="Inscribir estudiantes en lote",
    description=(
        "Vincula varios estudiantes a un mismo salón y año académico en una sola operación. "
        "Los que ya estuvieran inscritos se omiten sin error."
    ),
    responses={**PROTECTED_DETAIL_RESPONSES, **BAD_REQUEST},
)
def bulk_register_students_to_classroom(
    payload: BulkClassroomRegistrationCreate,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """Inscribe varios estudiantes en un salón, omitiendo los ya inscritos.

    Multi-tenancy:
        La inscripción es lo que ata a cada estudiante a una escuela, vía el salón.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(404): Si el salón no existe o está eliminado.
        HTTPException(400): Si el salón no pertenece al año académico indicado.
        HTTPException(500): Si la inserción masiva no devuelve filas.
    """
    msg = admin_service.bulk_register_students_to_classroom(payload)
    return APIResponse(data=msg, message="Vinculación masiva completada")


# ──────────────────────────────────────────────────────────
# GET: Schools
# ──────────────────────────────────────────────────────────

@router.get("/", response_model=APIResponse[PaginatedSchoolsResponse],
    summary="Listar escuelas",
    description=(
        "Retorna de forma paginada todas las escuelas no eliminadas. La paginación viaja "
        "anidada dentro de 'data' (formato legado)."
    ),
    responses=PROTECTED_DETAIL_RESPONSES,
)
def get_schools(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """Lista de forma paginada todas las escuelas registradas.

    Multi-tenancy:
        Vista global del administrador de sistema: no hay filtro por escuela, el rol audita y administra todas las instituciones.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(404): Si no hay ninguna escuela registrada. Devolver 404 ante
            una colección vacía es comportamiento legado; se sigue en el issue #15.
    """
    result = admin_service.get_schools(page=page, size=size)
    return APIResponse(data=result, message="Escuelas obtenidas exitosamente")

@router.get("/{school_id}", response_model=APIResponse[SchoolRead],
    summary="Obtener detalle de una escuela",
    description="Retorna los datos completos de una escuela a partir de su ID.",
    responses=PROTECTED_DETAIL_RESPONSES,
)
def get_school_detail(
    school_id: int,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """Devuelve el detalle completo de una escuela.

    Multi-tenancy:
        Excepción documentada: el 'school_id' se acepta por path porque la ruta está
        tras el gate de admin_sistema, cuyo alcance es global.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(404): Si no existe ninguna escuela con ese ID.
    """
    result = admin_service.get_school_detail(school_id=school_id)
    return APIResponse(data=result, message="Detalle de escuela obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET: Classrooms
# ──────────────────────────────────────────────────────────

@router.get("/classrooms/", response_model=APIResponse[PaginatedClassroomsResponse],
    summary="Listar salones de clase",
    description=(
        "Retorna de forma paginada los salones no eliminados de todas las escuelas, cada uno "
        "con su año académico y su escuela. La paginación viaja anidada dentro de 'data'."
    ),
    responses=PROTECTED_DETAIL_RESPONSES,
)
def get_classrooms(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """Lista de forma paginada los salones de todas las escuelas.

    Multi-tenancy:
        Vista global del administrador de sistema: no hay filtro por escuela, el rol audita y administra todas las instituciones.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(404): Si no hay ningún salón registrado. Comportamiento legado;
            se sigue en el issue #15.
    """
    result = admin_service.get_classrooms(page=page, size=size)
    return APIResponse(data=result, message="Salones de clase obtenidos exitosamente")

@router.get("/classrooms/{classroom_id}", response_model=APIResponse[ClassroomRead],
    summary="Obtener detalle de un salón",
    description="Retorna un salón con sus datos base, su año académico y su escuela.",
    responses=PROTECTED_DETAIL_RESPONSES,
)
def get_classroom_detail(
    classroom_id: int,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """Devuelve el detalle completo de un salón de clase.

    Multi-tenancy:
        Alcance global: puede consultar salones de cualquier escuela.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(404): Si no existe ningún salón con ese ID.
    """
    result = admin_service.get_classroom_detail(classroom_id=classroom_id)
    return APIResponse(data=result, message="Detalle del salón obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET: Students
# ──────────────────────────────────────────────────────────

@router.get("/students/", response_model=APIResponse[PaginatedStudentsResponse],
    summary="Listar estudiantes",
    description=(
        "Retorna de forma paginada los estudiantes no eliminados de todas las escuelas, cada "
        "uno con su escuela y su salón actual. La paginación viaja anidada dentro de 'data'."
    ),
    responses=PROTECTED_DETAIL_RESPONSES,
)
def get_students(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """Lista de forma paginada los estudiantes de todas las escuelas.

    Multi-tenancy:
        Vista global del administrador de sistema: no hay filtro por escuela, el rol audita y administra todas las instituciones.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(404): Si no hay ningún estudiante registrado. Comportamiento
            legado; se sigue en el issue #15.
    """
    result = admin_service.get_students(page=page, size=size)
    return APIResponse(data=result, message="Estudiantes obtenidos exitosamente")

@router.get("/students/{student_id}", response_model=APIResponse[StudentRead],
    summary="Obtener detalle de un estudiante",
    description="Retorna un estudiante con sus datos base, su escuela y su salón de clase vinculados.",
    responses=PROTECTED_DETAIL_RESPONSES,
)
def get_student_detail(
    student_id: int,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """Devuelve el detalle completo de un estudiante.

    Multi-tenancy:
        Alcance global: puede consultar estudiantes de cualquier escuela.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(404): Si no existe ningún estudiante con ese ID.
    """
    result = admin_service.get_student_detail(student_id=student_id)
    return APIResponse(data=result, message="Detalle del estudiante obtenido exitosamente")
