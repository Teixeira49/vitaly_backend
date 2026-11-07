"""
Tests for School Admin Classrooms endpoints and service layer:
  - GET /api/v1/school-admin/classrooms/ (get_academic_grades)
  - GET /api/v1/school-admin/classrooms/{classroom_id}/students (get_students_by_classroom)
  - GET /api/v1/school-admin/classrooms/categories-summary (get_classroom_categories_summary)
  - GET /api/v1/school-admin/classrooms/categories-available (get_available_classroom_categories)
  - GET /api/v1/school-admin/classrooms/categories/{category_id}/levels/{level}/sections (get_sections_by_category_and_level)

Adheres strictly to the 5 laws of vitaly-feature-testing:
  1. APIResponse envelope verification.
  2. Multi-tenancy isolation via server-resolved school_id (403 foreign school).
  3. Deterministic supabase-py mock.
  4. 404 for missing single entities / 200 with empty list for empty collections.
  5. RBAC matrix: 403 unauthorized role, 401 unauthenticated, 422 schema validation.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.deps import get_current_admin_escuela, get_current_user_token
from app.core.security import create_access_token
from app.main import app
from app.services.auth_service import auth_service
from app.services.school_admin_service import school_admin_service

SERVICE_MODULE = "app.services.school_admin_service"
BASE_URL = "/api/v1/school-admin/classrooms"
SCHOOL_ID = 1
OTHER_SCHOOL_ID = 99


# ──────────────────────────────────────────────────────────
# Helpers: realistic JWT payloads and chainable supabase-py mock
# ──────────────────────────────────────────────────────────

def admin_payload(user_id: int = 4) -> dict:
    """Claims present in JWT for admin_escuela (no school_id in JWT)."""
    return {
        "sub": str(user_id),
        "email": "admin@colegio.test",
        "role": "admin_escuela",
        "scope": "client",
        "name": "Laura Pérez",
        "gender": "FEMENINO",
        "administrative_position": "Directora",
        "school": "Colegio San Ignacio",
    }


def make_query(data=None, count=None) -> MagicMock:
    """Chainable mock for supabase-py queries."""
    query = MagicMock()
    for method in (
        "select", "eq", "neq", "in_", "is_", "ilike", "gte", "lte",
        "order", "range", "limit", "insert", "update", "delete", "or_"
    ):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=[] if data is None else data, count=count)
    return query


def route_tables(mock_supabase: MagicMock, **tables: MagicMock) -> None:
    """Route supabase.table(...) calls to table-specific query mocks."""
    mock_supabase.table.side_effect = lambda name: tables.get(name, make_query([]))


# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────

@pytest.fixture
def admin_client():
    """Client with get_current_admin_escuela overridden."""
    app.dependency_overrides[get_current_admin_escuela] = lambda: admin_payload()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Client with no overrides: real authentication/RBAC gates run."""
    app.dependency_overrides.clear()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────
# 1. GET / - Grados Académicos (get_academic_grades)
# ──────────────────────────────────────────────────────────

def test_get_academic_grades_endpoint_success(admin_client):
    """Verifica que el endpoint devuelva 200 con el envelope APIResponse y datos esperados."""
    fake_data = {
        "data": [
            {
                "id": 10,
                "category": 1,
                "level": 1,
                "section": "A",
                "is_deleted": False,
                "academic_year": {"id": 1, "name": "2025-2026"}
            }
        ],
        "total": 1,
        "page": 1,
        "size": 20,
        "academic_year": {"id": 1, "name": "2025-2026"}
    }
    with patch.object(school_admin_service, "get_academic_grades", return_value=fake_data) as mock_svc:
        response = admin_client.get(f"{BASE_URL}/?page=1&size=20")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Grados académicos obtenidos exitosamente" in body["message"]
    assert body["data"]["total"] == 1
    assert len(body["data"]["data"]) == 1
    mock_svc.assert_called_once_with(user_id=4, page=1, size=20)


def test_get_academic_grades_service_success():
    """Prueba la lógica del servicio con mocks de base de datos."""
    current_ay = {"id": 1, "name": "2025-2026"}
    classrooms = [{"id": 10, "category": 1, "level": 1, "section": "A", "is_deleted": False}]

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            academic_year=make_query([current_ay]),
            classroom=make_query(classrooms, count=1)
        )
        result = school_admin_service.get_academic_grades(user_id=4, page=1, size=20)

    assert result["total"] == 1
    assert result["page"] == 1
    assert result["academic_year"] == current_ay
    assert result["data"][0]["academic_year"] == current_ay


def test_get_academic_grades_no_current_academic_year():
    """Lanza 404 si no hay año académico vigente."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            academic_year=make_query([])  # No current year
        )
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_academic_grades(user_id=4, page=1, size=20)

    assert exc.value.status_code == 404
    assert "año académico vigente" in exc.value.detail


def test_get_academic_grades_no_classrooms_found():
    """Lanza 404 si la escuela no tiene aulas en el año vigente."""
    current_ay = {"id": 1, "name": "2025-2026"}
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            academic_year=make_query([current_ay]),
            classroom=make_query([], count=0)
        )
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_academic_grades(user_id=4, page=1, size=20)

    assert exc.value.status_code == 404
    assert "no tiene grados registrados" in exc.value.detail


# ──────────────────────────────────────────────────────────
# 2. GET /{classroom_id}/students (get_students_by_classroom)
# ──────────────────────────────────────────────────────────

def test_get_students_by_classroom_endpoint_success(admin_client):
    """Verifica respuesta 200 con envelope para estudiantes del aula."""
    fake_data = {
        "classroom": {"id": 5, "school_id": SCHOOL_ID},
        "data": [
            {
                "id": 101,
                "name": "Carlos",
                "lastname": "Gómez",
                "bmi_status": "OPTIMO",
                "has_active_medical_case": False
            }
        ],
        "total": 1,
        "page": 1,
        "size": 20
    }
    with patch.object(school_admin_service, "get_students_by_classroom", return_value=fake_data):
        response = admin_client.get(f"{BASE_URL}/5/students?page=1&size=20")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Estudiantes del salón obtenidos exitosamente" in body["message"]
    assert body["data"]["classroom"]["id"] == 5
    assert len(body["data"]["data"]) == 1


def test_get_students_by_classroom_service_success():
    """Verifica enriquecimiento con casos médicos activos y cálculo de IMC."""
    classroom_row = {
        "id": 5,
        "school_id": SCHOOL_ID,
        "category": 1,
        "level": 1,
        "section": "A",
        "academic_year_id": 1
    }
    students_rows = [
        {"id": 101, "name": "Carlos", "lastname": "Gómez", "birthday": "2015-05-10"},
        {"id": 102, "name": "Ana", "lastname": "Pérez", "birthday": "2015-06-12"}
    ]
    registrations = [{"student_id": 101}, {"student_id": 102}]
    # 101 has active case
    active_cases = [{"student_id": 101}]
    # 101 has optimal BMI (20.0), 102 has underweight BMI (15.0)
    # BMI = weight / (height/100)^2:
    # 101: 50kg / (1.58m)^2 = ~20.0 (OPTIMO)
    # 102: 30kg / (1.50m)^2 = 13.3 (DESNUTRIDO)
    metrics_rows = [
        {"student_id": 101, "weight": 50.0, "height": 158.0},
        {"student_id": 102, "weight": 30.0, "height": 150.0}
    ]

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            classroom=make_query([classroom_row]),
            classroom_registration=make_query(registrations, count=2),
            student=make_query(students_rows),
            medical_case=make_query(active_cases),
            student_metrics=make_query(metrics_rows)
        )
        result = school_admin_service.get_students_by_classroom(
            user_id=4, classroom_id=5, page=1, size=20
        )

    assert result["total"] == 2
    data = result["data"]
    s101 = next(s for s in data if s["id"] == 101)
    s102 = next(s for s in data if s["id"] == 102)

    assert s101["has_active_medical_case"] is True
    assert s101["bmi_status"] == "OPTIMO"

    assert s102["has_active_medical_case"] is False
    assert s102["bmi_status"] == "DESNUTRIDO"


def test_get_students_by_classroom_foreign_school_returns_403():
    """Multi-tenancy: el salón pertenece a otra escuela -> 403 Forbidden."""
    classroom_row = {
        "id": 8,
        "school_id": OTHER_SCHOOL_ID,
        "category": 1,
        "level": 1,
        "section": "B",
        "academic_year_id": 1
    }
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, classroom=make_query([classroom_row]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_students_by_classroom(
                user_id=4, classroom_id=8, page=1, size=20
            )

    assert exc.value.status_code == 403
    assert "otra escuela" in exc.value.detail


def test_get_students_by_classroom_not_found_returns_404():
    """Salón inexistente -> 404 Not Found."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, classroom=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_students_by_classroom(
                user_id=4, classroom_id=999, page=1, size=20
            )

    assert exc.value.status_code == 404
    assert "No existe ningún salón" in exc.value.detail


# ──────────────────────────────────────────────────────────
# 3. GET /categories-summary (get_classroom_categories_summary)
# ──────────────────────────────────────────────────────────

def test_get_classroom_categories_summary_success(admin_client):
    """Valida retorno 200 con resumen de categorías y niveles."""
    current_ay = {"id": 1, "name": "2025-2026"}
    classroom_rows = [
        {
            "level": 1,
            "category": 1,
            "classroom_category": {"id": 1, "classroom_type_name": "PRIMARIA"}
        },
        {
            "level": 2,
            "category": 1,
            "classroom_category": {"id": 1, "classroom_type_name": "PRIMARIA"}
        }
    ]
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            academic_year=make_query([current_ay]),
            classroom=make_query(classroom_rows)
        )
        response = admin_client.get(f"{BASE_URL}/categories-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]["items"]) == 2
    assert body["data"]["items"][0]["classroom_type_name"] == "PRIMARIA"


def test_get_classroom_categories_summary_empty(admin_client):
    """Colección vacía -> 200 con items=[]."""
    current_ay = {"id": 1, "name": "2025-2026"}
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            academic_year=make_query([current_ay]),
            classroom=make_query([])
        )
        response = admin_client.get(f"{BASE_URL}/categories-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["items"] == []


# ──────────────────────────────────────────────────────────
# 4. GET /categories-available (get_available_classroom_categories)
# ──────────────────────────────────────────────────────────

def test_get_available_classroom_categories_success(admin_client):
    """Retorna categorías únicas disponibles para el colegio en el año vigente."""
    current_ay = {"id": 1, "name": "2025-2026"}
    classroom_rows = [
        {"category": 1, "classroom_category": {"id": 1, "classroom_type_name": "PRIMARIA"}},
        {"category": 2, "classroom_category": {"id": 2, "classroom_type_name": "SECUNDARIA"}}
    ]
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            academic_year=make_query([current_ay]),
            classroom=make_query(classroom_rows)
        )
        response = admin_client.get(f"{BASE_URL}/categories-available")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert len(items) == 2
    assert items[0]["classroom_type_name"] == "PRIMARIA"
    assert items[1]["classroom_type_name"] == "SECUNDARIA"


def test_get_available_classroom_categories_no_academic_year():
    """Lanza 404 si no hay año académico vigente configurado."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, academic_year=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_available_classroom_categories(user_id=4)

    assert exc.value.status_code == 404
    assert "año académico vigente" in exc.value.detail


# ──────────────────────────────────────────────────────────
# 5. GET /categories/{category_id}/levels/{level}/sections
# ──────────────────────────────────────────────────────────

def test_get_sections_by_category_and_level_success(admin_client):
    """Devuelve las secciones configuradas para una categoría y nivel."""
    sections_rows = [
        {"id": 10, "section": "A"},
        {"id": 11, "section": "B"}
    ]
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, classroom=make_query(sections_rows))
        response = admin_client.get(f"{BASE_URL}/categories/1/levels/3/sections")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert len(items) == 2
    assert items[0]["section"] == "A"
    assert items[1]["section"] == "B"


def test_get_sections_with_active_year(admin_client):
    """Cuando active=True, filtra por el año académico vigente."""
    current_ay = {"id": 5, "name": "2025-2026"}
    sections_rows = [{"id": 10, "section": "A"}]
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            academic_year=make_query([current_ay]),
            classroom=make_query(sections_rows)
        )
        response = admin_client.get(f"{BASE_URL}/categories/1/levels/3/sections?active=true")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]["items"]) == 1


# ──────────────────────────────────────────────────────────
# 6. RBAC & Autenticación
# ──────────────────────────────────────────────────────────

def test_classrooms_unauthenticated_returns_401(client):
    """Sin credenciales -> 401."""
    response = client.get(f"{BASE_URL}/")
    assert response.status_code == 401


def test_classrooms_invalid_jwt_returns_401(client):
    """Token malformado -> 401."""
    response = client.get(
        f"{BASE_URL}/",
        headers={"Authorization": "Bearer token-invalido-xyz"}
    )
    assert response.status_code == 401


def test_classrooms_revoked_jwt_returns_401(client):
    """Token revocado -> 401."""
    token = create_access_token({"sub": "4", "role": "admin_escuela"})
    with patch.object(auth_service, "is_token_revoked", return_value=True):
        response = client.get(
            f"{BASE_URL}/",
            headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 401


def test_classrooms_wrong_role_returns_403(client):
    """Rol incompatible (ej. representante o doctor) -> 403 Forbidden."""
    app.dependency_overrides[get_current_user_token] = lambda: {
        "sub": "20",
        "role": "representante",
        "scope": "client"
    }
    response = client.get(f"{BASE_URL}/")
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False


def test_classrooms_admin_unlinked_to_school_returns_403(admin_client):
    """Admin sin escuela vinculada -> 403 Forbidden."""
    with patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        # school_administrator table returns empty
        route_tables(mock_supabase, school_administrator=make_query([]))
        response = admin_client.get(f"{BASE_URL}/")

    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert "no está vinculado a ninguna escuela" in body["message"]


# ──────────────────────────────────────────────────────────
# 7. Validación de parámetros (422)
# ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("invalid_url", [
    f"{BASE_URL}/?page=0",                 # page ge=1
    f"{BASE_URL}/?size=500",               # size le=100
    f"{BASE_URL}/abc/students",            # classroom_id not int
    f"{BASE_URL}/categories/abc/levels/1/sections",  # category_id not int
    f"{BASE_URL}/categories/1/levels/abc/sections",  # level not int
])
def test_classrooms_validation_errors(admin_client, invalid_url):
    """Parámetros no conformes devuelven 422 con formato estándar."""
    response = admin_client.get(invalid_url)
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
