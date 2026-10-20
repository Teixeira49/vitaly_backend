"""
Tests for School Admin Profile and Dashboard endpoints and service layer:
  - GET /api/v1/school-admin/profile (get_my_profile)
  - PUT /api/v1/school-admin/profile (update_my_profile)
  - GET /api/v1/school-admin/students/resume (get_students_resume)
  - GET /api/v1/school-admin/students/{student_id}/medical-history (get_student_medical_history)

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
BASE_URL = "/api/v1/school-admin"
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
# 1. PERFIL: GET y PUT /profile
# ──────────────────────────────────────────────────────────

def test_get_my_profile_endpoint_success(admin_client):
    """Verifica respuesta 200 con envelope para consulta de perfil propio."""
    fake_data = {
        "user_info": {
            "name": "Laura",
            "lastname": "Pérez",
            "email": "admin@colegio.test"
        },
        "admin_info": {"administrative_position": "Directora"},
        "school_info": {"name": "Colegio San Ignacio"}
    }
    with patch.object(school_admin_service, "get_my_profile", return_value=fake_data) as mock_svc:
        response = admin_client.get(f"{BASE_URL}/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Perfil obtenido exitosamente" in body["message"]
    assert body["data"]["user_info"]["name"] == "Laura"
    mock_svc.assert_called_once_with(user_id=4)


def test_get_my_profile_service_success():
    """Valida obtención de perfil con saneamiento de credenciales."""
    admin_row = {
        "id": 1,
        "school_id": SCHOOL_ID,
        "administrative_position": "Coordinadora",
        "user": {
            "id": 4,
            "name": "Laura",
            "lastname": "Pérez",
            "email": "admin@colegio.test",
            "password": "hashed_secret",
            "photo_file_id": "file_xyz"
        },
        "school": {
            "name": "Colegio San Ignacio",
            "year_foundation": 1953,
            "address": "Av. Principal"
        }
    }

    with patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, school_administrator=make_query([admin_row]))
        result = school_admin_service.get_my_profile(user_id=4)

    assert result["user_info"]["name"] == "Laura"
    assert "password" not in result["user_info"]
    assert "photo_file_id" not in result["user_info"]
    assert result["school_info"]["name"] == "Colegio San Ignacio"


def test_get_my_profile_not_found_returns_404():
    """Admin no registrado en school_administrator -> 404 Not Found."""
    with patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, school_administrator=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_my_profile(user_id=999)

    assert exc.value.status_code == 404
    assert "Perfil de administrador no encontrado" in exc.value.detail


def test_update_my_profile_endpoint_success(admin_client):
    """Verifica actualización de perfil vía PUT."""
    fake_data = {
        "user_info": {"name": "Laura Elena", "lastname": "Pérez"},
        "admin_info": {},
        "school_info": {}
    }
    payload = {"name": "Laura Elena"}
    with patch.object(school_admin_service, "update_my_profile", return_value=fake_data) as mock_svc:
        response = admin_client.put(f"{BASE_URL}/profile", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Perfil actualizado exitosamente" in body["message"]
    assert body["data"]["user_info"]["name"] == "Laura Elena"
    mock_svc.assert_called_once()


def test_update_my_profile_service_success():
    """Valida actualización en tabla user y retorno del perfil enriquecido."""
    user_query = make_query([{"id": 4}])
    with patch.object(school_admin_service, "get_my_profile", return_value={"updated": True}), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, user=user_query)
        result = school_admin_service.update_my_profile(
            user_id=4,
            payload={"name": "Nuevo Nombre", "biography": "Bio actualizada"}
        )

    assert result["updated"] is True
    user_query.update.assert_called_once()


# ──────────────────────────────────────────────────────────
# 2. DASHBOARD: GET /students/resume
# ──────────────────────────────────────────────────────────

def test_get_students_resume_endpoint_success(admin_client):
    """Verifica respuesta 200 con envelope para resumen métrico de la escuela."""
    fake_data = {
        "total_students": 100,
        "overweight_students": 10,
        "malnourished_students": 5,
        "active_cases": 3,
        "optimal_students": 85
    }
    with patch.object(school_admin_service, "get_students_resume", return_value=fake_data) as mock_svc:
        response = admin_client.get(f"{BASE_URL}/students/resume")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Resumen de estudiantes obtenido exitosamente" in body["message"]
    data = body["data"]
    assert data["total_students"] == 100
    assert data["optimal_students"] == 85
    mock_svc.assert_called_once()


def test_get_students_resume_service_calculation():
    """Prueba fórmulas de nutrición (IMC < 18.5 desnutrido, > 24.9 sobrepeso, resto óptimo)."""
    ay_row = {"id": 1}
    classroom_rows = [{"id": 10}, {"id": 20}]
    reg_rows = [{"student_id": 1}, {"student_id": 2}, {"student_id": 3}]

    # 1: 30kg / 1.50m^2 = 13.3 (malnourished)
    # 2: 70kg / 1.60m^2 = 27.3 (overweight)
    # 3: 50kg / 1.60m^2 = 19.5 (optimal)
    metrics_rows = [
        {"student_id": 1, "weight": 30.0, "height": 150.0},
        {"student_id": 2, "weight": 70.0, "height": 160.0},
        {"student_id": 3, "weight": 50.0, "height": 160.0}
    ]
    cases_rows = [{"id": 100}]

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            academic_year=make_query([ay_row]),
            classroom=make_query(classroom_rows),
            classroom_registration=make_query(reg_rows),
            student_metrics=make_query(metrics_rows),
            medical_case=make_query(cases_rows)
        )
        result = school_admin_service.get_students_resume(user_id=4)

    assert result["total_students"] == 3
    assert result["malnourished_students"] == 1
    assert result["overweight_students"] == 1
    assert result["optimal_students"] == 1
    assert result["active_cases"] == 1


def test_get_students_resume_hierarchical_filters():
    """Valida aplicación de filtros jerárquicos (category -> grade -> section)."""
    ay_row = {"id": 1}
    classroom_query = make_query([{"id": 10}])

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            academic_year=make_query([ay_row]),
            classroom=classroom_query,
            classroom_registration=make_query([]),
            student_metrics=make_query([]),
            medical_case=make_query([])
        )
        result = school_admin_service.get_students_resume(
            user_id=4, category=1, grade=2, section="A"
        )

    assert result["total_students"] == 0
    classroom_query.eq.assert_any_call("category", 1)
    classroom_query.eq.assert_any_call("level", 2)
    classroom_query.eq.assert_any_call("section", "A")


def test_get_students_resume_invalid_filter_dependencies():
    """Rechaza combinaciones ilegales de filtros jerárquicos con 400 Bad Request."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID):
        # Grade without category
        with pytest.raises(HTTPException) as exc1:
            school_admin_service.get_students_resume(user_id=4, grade=3)
        assert exc1.value.status_code == 400
        assert "requiere que 'category' también sea proporcionado" in exc1.value.detail

        # Section without grade or category
        with pytest.raises(HTTPException) as exc2:
            school_admin_service.get_students_resume(user_id=4, category=1, section="B")
        assert exc2.value.status_code == 400
        assert "requiere que 'category' y 'grade'" in exc2.value.detail


def test_get_students_resume_no_current_academic_year():
    """Lanza 404 si el sistema no tiene un año académico vigente configurado."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, academic_year=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_students_resume(user_id=4)

    assert exc.value.status_code == 404
    assert "año académico vigente" in exc.value.detail


# ──────────────────────────────────────────────────────────
# 3. HISTORIAL MÉDICO: GET /students/{id}/medical-history
# ──────────────────────────────────────────────────────────

def test_get_student_medical_history_endpoint_success(admin_client):
    """Verifica respuesta 200 con envelope para historial médico del alumno."""
    fake_data = {
        "data": [
            {
                "id": 10,
                "start_date": "2026-03-01",
                "type_of_case": "ALERGIA",
                "is_active": True,
                "title": "Alergia estacional",
                "description": "Estornudos"
            }
        ],
        "total": 1,
        "page": 1,
        "size": 20
    }
    with patch.object(school_admin_service, "get_student_medical_history", return_value=fake_data):
        response = admin_client.get(f"{BASE_URL}/students/10/medical-history?page=1&size=20")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Historial médico obtenido exitosamente" in body["message"]
    assert body["data"]["total"] == 1


def test_get_student_medical_history_foreign_school_returns_403():
    """Estudiante no inscrito en ningún aula de la escuela del admin -> 403 Forbidden."""
    school_classrooms = [{"id": 1}]
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            classroom=make_query(school_classrooms),
            classroom_registration=make_query([])  # Student not in school's classrooms
        )
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_student_medical_history(
                user_id=4, student_id=999, page=1, size=20
            )

    assert exc.value.status_code == 403
    assert "no está en su escuela" in exc.value.detail


def test_get_student_medical_history_empty_cases():
    """Alumno sin casos médicos retorna 200 con data=[] (regla empty-table-validation)."""
    school_classrooms = [{"id": 1}]
    reg_rows = [{"id": 50}]
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            classroom=make_query(school_classrooms),
            classroom_registration=make_query(reg_rows),
            medical_case=make_query([], count=0)
        )
        result = school_admin_service.get_student_medical_history(
            user_id=4, student_id=10, page=1, size=20
        )

    assert result["data"] == []
    assert result["total"] == 0


# ──────────────────────────────────────────────────────────
# 4. RBAC & Autenticación
# ──────────────────────────────────────────────────────────

def test_profile_unauthenticated_returns_401(client):
    """Sin credenciales -> 401."""
    response = client.get(f"{BASE_URL}/profile")
    assert response.status_code == 401


def test_profile_invalid_jwt_returns_401(client):
    """Token malformado -> 401."""
    response = client.get(
        f"{BASE_URL}/profile",
        headers={"Authorization": "Bearer token-falso"}
    )
    assert response.status_code == 401


def test_profile_revoked_jwt_returns_401(client):
    """Token revocado -> 401."""
    token = create_access_token({"sub": "4", "role": "admin_escuela"})
    with patch.object(auth_service, "is_token_revoked", return_value=True):
        response = client.get(
            f"{BASE_URL}/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 401


def test_profile_wrong_role_returns_403(client):
    """Rol no autorizado -> 403 Forbidden."""
    app.dependency_overrides[get_current_user_token] = lambda: {
        "sub": "20",
        "role": "doctor",
        "scope": "client"
    }
    response = client.get(f"{BASE_URL}/profile")
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False


def test_dashboard_admin_unlinked_returns_403(admin_client):
    """Admin sin escuela vinculada -> 403 Forbidden."""
    with patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, school_administrator=make_query([]))
        response = admin_client.get(f"{BASE_URL}/students/resume")

    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert "no está vinculado a ninguna escuela" in body["message"]


# ──────────────────────────────────────────────────────────
# 5. Validación de parámetros (422)
# ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("invalid_url", [
    f"{BASE_URL}/students/abc/medical-history",                 # student_id not int
    f"{BASE_URL}/students/10/medical-history?page=0",           # page ge=1
    f"{BASE_URL}/students/10/medical-history?size=500",         # size le=100
    f"{BASE_URL}/students/resume?category=abc",                 # category not int
    f"{BASE_URL}/students/resume?grade=abc",                    # grade not int
])
def test_profile_dashboard_validation_errors(admin_client, invalid_url):
    """Parámetros no conformes devuelven 422 con formato estándar."""
    response = admin_client.get(invalid_url)
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
