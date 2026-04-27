from datetime import date
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from app.api.deps import get_current_admin_escuela
from app.schemas.responses import APIResponse
from app.schemas.student import StudentUpdateSchoolAdmin
from app.services.school_admin_service import school_admin_service

router = APIRouter()


# ──────────────────────────────────────────────────────────
# GET - Mi Perfil de Administrador
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
# GET - Tendencia de casos médicos (mensual / semanal)
# ──────────────────────────────────────────────────────────

@router.get("/students/medical-cases-tendency", response_model=APIResponse[dict])
def get_medical_cases_tendency(
    mode: str = Query("monthly", description="Modo de agrupación: 'monthly' o 'weekly'"),
    months: int = Query(3, ge=1, le=24, description="Meses hacia atrás a analizar (modo monthly)"),
    weeks: int = Query(12, ge=1, le=52, description="Semanas hacia atrás a analizar (modo weekly)"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Tendencia de nuevos casos médicos en el tiempo para los estudiantes de la escuela.

    - **mode=monthly** (default): agrupa por mes, analiza los últimos `months` meses (default 3).
    - **mode=weekly**: agrupa por semana ISO, analiza las últimas `weeks` semanas (default 12).

    Retorna:
    - `summary.total_incidents`: total de casos en el período.
    - `summary.growth_rate`: % de crecimiento respecto al período inmediatamente anterior de igual duración.
    - `data[].label`: nombre del mes (Ene, Feb…) o número de semana (Sem 15…).
    - `data[].value`: cantidad de casos en ese período.
    - `data[].trend`: valor de la línea de tendencia lineal (regresión y = mx + b).

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_medical_cases_tendency(
        user_id=user_id,
        mode=mode,
        months=months,
        weeks=weeks,
    )
    return APIResponse(data=result, message="Tendencia de casos médicos obtenida exitosamente")


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
# GET - Búsqueda / Filtrado de casos médicos (con filtros)
# ──────────────────────────────────────────────────────────

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
    page: int = Query(1, ge=1, description="Número de página (empieza en 1)."),
    size: int = Query(20, ge=1, le=100, description="Elementos por página (máximo 100)."),
    admin_payload: dict = Depends(get_current_admin_escuela),
):
    """
    Búsqueda paginada de casos médicos de la escuela con filtros opcionales e independientes.

    **Filtros disponibles:**
    - **status**: `activo` (end_date o final_diagnosis es nulo) / `resuelto` (ambos no nulos).
    - **type_of_case**: `ALERGIA`, `LESION`, `ENFERMEDAD` o `EMERGENCIA`.
    - **date_from**: Filtra casos cuya fecha de inicio sea ≥ a este valor.
    - **date_to**: Filtra casos cuya fecha de inicio sea ≤ a este valor.
    - Se puede usar `date_from` sin `date_to` y viceversa.

    **Cada caso en la respuesta incluye:**
    - `id`, `status`, `start_date`, `student_name`, `type_of_case`, `description`

    Solo se devuelven casos no eliminados (`is_deleted = false`) de estudiantes
    pertenecientes a la escuela administrada por el usuario autenticado.

    Requiere JWT (admin_escuela).
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
    )
    return APIResponse(data=result, message="Búsqueda de casos médicos completada exitosamente")


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


# ──────────────────────────────────────────────────────────
# GET - Resumen de categorías/niveles del año académico vigente
# ──────────────────────────────────────────────────────────

@router.get("/classrooms/categories-summary", response_model=APIResponse[dict])
def get_classroom_categories_summary(
    category_id: int = Query(None, description="ID de la categoría para filtrar los niveles (opcional)."),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Retorna las combinaciones únicas de (level, classroom_category_id, classroom_type_name)
    presentes en los salones de la escuela para el año académico vigente.

    Si se proporciona `category_id`, el resultado se filtrará para devolver únicamente 
    los niveles correspondientes a esa categoría específica.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_classroom_categories_summary(
        user_id=user_id,
        category_id=category_id
    )
    return APIResponse(data=result, message="Resumen de categorías obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Lista simple de categorías disponibles para la escuela
# ──────────────────────────────────────────────────────────

@router.get("/classrooms/categories-available", response_model=APIResponse[dict])
def get_available_classroom_categories(
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Retorna la lista única de categorías (PREESCOLAR, PRIMARIA, etc.) disponibles 
    en la escuela para el año académico vigente.
    
    A diferencia de /categories-summary, este endpoint no incluye los niveles (grados),
    solo las categorías principales.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_available_classroom_categories(user_id=user_id)
    return APIResponse(data=result, message="Categorías disponibles obtenidas exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Secciones disponibles para una categoría y nivel dados
# ──────────────────────────────────────────────────────────

@router.get("/classrooms/categories/{category_id}/levels/{level}/sections", response_model=APIResponse[dict])
def get_sections_by_category_and_level(
    category_id: int,
    level: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Retorna las secciones disponibles en el año académico vigente para una combinación
    específica de classroom_category (category_id) y level.

    Ejemplo: category_id=1, level=3 → secciones A, B, C disponibles.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_sections_by_category_and_level(
        user_id=user_id,
        category_id=category_id,
        level=level
    )
    return APIResponse(data=result, message="Secciones obtenidas exitosamente")
