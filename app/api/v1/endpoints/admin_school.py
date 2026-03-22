from fastapi import APIRouter, Depends, Query
from typing import List
from app.api.deps import get_current_admin_sistema
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

@router.post("/", response_model=APIResponse[str])
def create_school(
    payload: SchoolCreate,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Agrega una nueva escuela a la plataforma (restringido a admin_sistema).
    Verifica que no exista el mismo nombre de escuela en el mismo estado, ni un RIF duplicado globalmente, y que el año de fundación sea válido.
    """
    msg = admin_service.create_school(payload)
    return APIResponse(data=msg, message="Registro completado")

@router.post("/classrooms", response_model=APIResponse[str])
def create_classroom(
    payload: ClassroomCreate,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Crea un salón de clase dentro de una escuela y año académico dados.
    Reglas de nivel por categoría (configurables en Settings):
    - Categoría 1 (Preescolar): niveles 1-3
    - Categoría 2 (Primaria):   niveles 1-6
    - Categoría 3 (Bachillerato): niveles 1-5
    La sección es opcional, máximo 3 caracteres alfanuméricos, se convierte a mayúsculas automáticamente.
    Solo admin_sistema puede acceder.
    """
    msg = admin_service.create_classroom(payload)
    return APIResponse(data=msg, message="Salón registrado exitosamente")

@router.post("/students", response_model=APIResponse[str])
def create_student(
    payload: StudentCreate,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Registra un nuevo estudiante en la plataforma.
    Restricciones:
    - El estudiante no puede ser mayor a 21 años según su fecha de nacimiento.
    - El género debe ser MASCULINO o FEMENINO.
    - El tipo de sangre debe ser uno de los tipos predefinidos (A+, A-, B+, B-, AB+, AB-, O+, O-).
    - Si se proporciona un número de cédula (identity_number), se valida que no exista otro estudiante activo con dicha CI.
    Solo admin_sistema puede acceder.
    """
    msg = admin_service.create_student(payload)
    return APIResponse(data=msg, message="Estudiante registrado exitosamente")

@router.patch("/students/{student_id}", response_model=APIResponse[str])
def update_student(
    student_id: int,
    payload: StudentUpdate,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Modifica los atributos de un estudiante existente. Solo se actualizan los campos enviados en el body.
    Campos no modificables: is_active, is_deleted.
    Restricciones:
    - birthday: no puede indicar más de 21 años de edad ni ser una fecha futura (Pydantic rechaza fechas imposibles como mes 13 automáticamente).
    - identity_number: si se cambia, se valida que no exista otro estudiante activo con la misma cédula.
    Solo admin_sistema puede acceder.
    """
    msg = admin_service.update_student(student_id=student_id, payload=payload)
    return APIResponse(data=msg, message="Estudiante actualizado exitosamente")

@router.post("/classrooms/register", response_model=APIResponse[str])
def register_student_to_classroom(
    payload: ClassroomRegistrationCreate,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Vincula a un estudiante a un salón de clase y año académico específicos.
    Por defecto, el estatus es 2 (Pendiente).
    Verifica que el salón corresponda al año académico indicado.
    Requiere JWT (admin_sistema).
    """
    msg = admin_service.register_student_to_classroom(payload)
    return APIResponse(data=msg, message="Estudiante vinculado al salón exitosamente")

@router.post("/classrooms/register/bulk", response_model=APIResponse[str])
def bulk_register_students_to_classroom(
    payload: BulkClassroomRegistrationCreate,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Vincula a múltiples estudiantes a un salón de clase y año académico de forma masiva.
    Evita duplicados si alguno de los estudiantes ya estaba registrado en ese salón.
    Requiere JWT (admin_sistema).
    """
    msg = admin_service.bulk_register_students_to_classroom(payload)
    return APIResponse(data=msg, message="Vinculación masiva completada")


# ──────────────────────────────────────────────────────────
# GET: Schools
# ──────────────────────────────────────────────────────────

@router.get("/", response_model=APIResponse[PaginatedSchoolsResponse])
def get_schools(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Lista paginada de todas las escuelas registradas (no eliminadas).
    Requiere JWT (admin_sistema).
    """
    result = admin_service.get_schools(page=page, size=size)
    return APIResponse(data=result, message="Escuelas obtenidas exitosamente")

@router.get("/{school_id}", response_model=APIResponse[SchoolRead])
def get_school_detail(
    school_id: int,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Detalle completo de una escuela por su ID.
    Requiere JWT (admin_sistema).
    """
    result = admin_service.get_school_detail(school_id=school_id)
    return APIResponse(data=result, message="Detalle de escuela obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET: Classrooms
# ──────────────────────────────────────────────────────────

@router.get("/classrooms/", response_model=APIResponse[PaginatedClassroomsResponse])
def get_classrooms(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Lista paginada de salones de clase con su año académico y escuela vinculada.
    Requiere JWT (admin_sistema).
    """
    result = admin_service.get_classrooms(page=page, size=size)
    return APIResponse(data=result, message="Salones de clase obtenidos exitosamente")

@router.get("/classrooms/{classroom_id}", response_model=APIResponse[ClassroomRead])
def get_classroom_detail(
    classroom_id: int,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Detalle completo de un salón: datos base, año académico y escuela.
    Requiere JWT (admin_sistema).
    """
    result = admin_service.get_classroom_detail(classroom_id=classroom_id)
    return APIResponse(data=result, message="Detalle del salón obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET: Students
# ──────────────────────────────────────────────────────────

@router.get("/students/", response_model=APIResponse[PaginatedStudentsResponse])
def get_students(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Lista paginada de estudiantes con nombre de su escuela y datos de su salón.
    Requiere JWT (admin_sistema).
    """
    result = admin_service.get_students(page=page, size=size)
    return APIResponse(data=result, message="Estudiantes obtenidos exitosamente")

@router.get("/students/{student_id}", response_model=APIResponse[StudentRead])
def get_student_detail(
    student_id: int,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Detalle completo de un estudiante: datos base, escuela y salón de clase vinculados.
    Requiere JWT (admin_sistema).
    """
    result = admin_service.get_student_detail(student_id=student_id)
    return APIResponse(data=result, message="Detalle del estudiante obtenido exitosamente")
