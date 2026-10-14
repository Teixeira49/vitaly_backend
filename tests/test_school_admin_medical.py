"""
Tests for School Admin Medical endpoints and service layer:
  - GET /api/v1/school-admin/doctors (get_doctors)
  - GET /api/v1/school-admin/doctors/{doctor_id} (get_doctor_detail)
  - PATCH /api/v1/school-admin/doctors/{doctor_id}/suspend (suspend_doctor)
  - PATCH /api/v1/school-admin/doctors/{doctor_id}/activate (reactivate_doctor)
  - GET /api/v1/school-admin/medical-cases (get_medical_cases)
  - GET /api/v1/school-admin/medical-cases/search (search_medical_cases)
  - GET /api/v1/school-admin/students/medical-cases/tendency (get_medical_cases_tendency)
  - GET /api/v1/school-admin/medical-cases/{case_id} (get_medical_case_detail)
  - GET /api/v1/school-admin/students/{student_id}/metrics (get_student_metrics_history)

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
# 1. DOCTORES: Listado, Detalle, Suspender y Activar
# ──────────────────────────────────────────────────────────

def test_get_doctors_endpoint_success(admin_client):
    """Verifica respuesta 200 con envelope para listado de médicos."""
    fake_data = {
        "data": [
            {
                "fullname": "Dr. Juan Pérez",
                "name": "Juan",
                "lastname": "Pérez",
                "specialty": "Pediatría",
                "medical_license": "MPPS-12345",
                "status": "Activo",
                "experience_years": 2015,
                "years_of_experience": 11
            }
        ],
        "total": 1,
        "page": 1,
        "size": 20
    }
    with patch.object(school_admin_service, "get_doctors", return_value=fake_data) as mock_svc:
        response = admin_client.get(f"{BASE_URL}/doctors?page=1&size=20")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Lista de doctores obtenida exitosamente" in body["message"]
    assert body["data"]["total"] == 1
    mock_svc.assert_called_once_with(user_id=4, page=1, size=20)


def test_get_doctors_service_success():
    """Prueba la lógica de enriquecimiento de doctores en el servicio."""
    d2s_rows = [{"doctor_id": 1, "status": 10}]
    doc_rows = [{
        "doc_id": 1,
        "user_id": 50,
        "doc_license_number": "MPPS-123",
        "especially": "Pediatra",
        "experience_years": 2010
    }]
    user_rows = [{
        "id": 50,
        "name": "Ana",
        "lastname": "Sucre",
        "gender": "FEMENINO",
        "photo_url": "https://img.test/photo.jpg"
    }]
    status_rows = [{"status_id": 10, "status_name": "Activo"}]

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            doctor_to_school=make_query(d2s_rows, count=1),
            doctor=make_query(doc_rows),
            user=make_query(user_rows),
            system_status=make_query(status_rows)
        )
        result = school_admin_service.get_doctors(user_id=4, page=1, size=20)

    assert result["total"] == 1
    doc = result["data"][0]
    assert doc["fullname"] == "Dra. Ana Sucre"
    assert doc["status"] == "Activo"
    assert doc["years_of_experience"] > 0


def test_get_doctors_empty_collection(admin_client):
    """Escuela sin doctores retorna 200 con lista vacía (regla empty-table-validation)."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, doctor_to_school=make_query([], count=0))
        response = admin_client.get(f"{BASE_URL}/doctors")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["data"] == []
    assert body["data"]["total"] == 0


def test_get_doctor_detail_success(admin_client):
    """Verifica detalle completo de un médico con información profesional y de usuario."""
    d2s_row = {"status": 1}
    doc_row = {
        "doc_id": 5,
        "doc_license_number": "LIC-999",
        "especially": "General",
        "experience_years": 2018,
        "user": {
            "id": 88,
            "name": "Carlos",
            "lastname": "Ramos",
            "gender": "MASCULINO",
            "email": "carlos@test.com"
        }
    }
    status_row = {"status_name": "Activo"}
    phone_rows = [{"phone_number": "+584141234567", "phone_category": "MÓVIL"}]

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            doctor_to_school=make_query([d2s_row]),
            doctor=make_query([doc_row]),
            system_status=make_query([status_row]),
            user_phones=make_query(phone_rows)
        )
        response = admin_client.get(f"{BASE_URL}/doctors/5")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["doctor_info"]["specialty"] == "General"
    assert body["data"]["user_info"]["fullname"] == "Dr. Carlos Ramos"
    assert len(body["data"]["user_info"]["phones"]) == 1


def test_get_doctor_detail_not_linked_to_school_returns_403():
    """Médico no vinculado a la escuela del administrador -> 403 Forbidden."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, doctor_to_school=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_doctor_detail(user_id=4, doctor_id=99)

    assert exc.value.status_code == 403
    assert "no pertenece a tu escuela" in exc.value.detail


def test_get_doctor_detail_not_found_returns_404():
    """Médico con vínculo pero sin registro en tabla doctor -> 404 Not Found."""
    d2s_row = {"status": 1}
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            doctor_to_school=make_query([d2s_row]),
            doctor=make_query([])  # Not found
        )
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_doctor_detail(user_id=4, doctor_id=99)

    assert exc.value.status_code == 404
    assert "No existe ningún médico" in exc.value.detail


def test_suspend_doctor_success(admin_client):
    """Suspende las labores de un médico cambiando status a 1."""
    d2s_query = make_query([{"id": 10}])
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, doctor_to_school=d2s_query)
        response = admin_client.patch(f"{BASE_URL}/doctors/5/suspend")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "suspendidas exitosamente" in body["message"]
    d2s_query.update.assert_called_once_with({"status": 1})


def test_suspend_doctor_not_linked_returns_404():
    """Intentar suspender un médico no vinculado a la escuela -> 404."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, doctor_to_school=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.suspend_doctor(user_id=4, doctor_id=99)

    assert exc.value.status_code == 404
    assert "no está vinculado a tu escuela" in exc.value.detail


def test_reactivate_doctor_success(admin_client):
    """Reactiva las labores de un médico cambiando status a 2."""
    d2s_query = make_query([{"id": 10}])
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, doctor_to_school=d2s_query)
        response = admin_client.patch(f"{BASE_URL}/doctors/5/activate")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "activado exitosamente" in body["message"]
    d2s_query.update.assert_called_once_with({"status": 2})


# ──────────────────────────────────────────────────────────
# 2. CASOS MÉDICOS: Listado, Búsqueda, Detalle y Tendencia
# ──────────────────────────────────────────────────────────

def test_get_medical_cases_endpoint_success(admin_client):
    """Verifica respuesta 200 con envelope para listado de casos médicos."""
    fake_data = {
        "data": [
            {
                "id": 1,
                "status": "activo",
                "start_date": "2026-02-01",
                "student_name": "Luis Morales",
                "type_of_case": "ALERGIA",
                "description": "Rinitis alérgica"
            }
        ],
        "total": 1,
        "page": 1,
        "size": 20
    }
    with patch.object(school_admin_service, "get_medical_cases", return_value=fake_data) as mock_svc:
        response = admin_client.get(f"{BASE_URL}/medical-cases?page=1&size=20")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Casos médicos obtenidos exitosamente" in body["message"]
    assert body["data"]["total"] == 1
    mock_svc.assert_called_once_with(user_id=4, page=1, size=20, current_year_only=False)


def test_get_medical_cases_empty(admin_client):
    """Sin casos médicos retorna 200 con lista vacía."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        # Classroom query returns empty
        route_tables(mock_supabase, classroom=make_query([]))
        response = admin_client.get(f"{BASE_URL}/medical-cases")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["data"] == []
    assert body["data"]["total"] == 0


def test_search_medical_cases_success(admin_client):
    """Búsqueda de casos con filtros retorna 200 y resultados coincidentes."""
    fake_data = {
        "data": [
            {
                "id": 2,
                "status": "resuelto",
                "type_of_case": "LESION",
                "init_date": "2026-01-10",
                "student_name": "Ana Gómez"
            }
        ],
        "total": 1,
        "page": 1,
        "size": 20
    }
    with patch.object(school_admin_service, "search_medical_cases", return_value=fake_data) as mock_svc:
        response = admin_client.get(
            f"{BASE_URL}/medical-cases/search?status=resuelto&type_of_case=LESION&page=1&size=20"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Búsqueda de casos médicos completada exitosamente" in body["message"]
    assert body["data"]["total"] == 1
    mock_svc.assert_called_once()


def test_search_medical_cases_empty(admin_client):
    """Búsqueda sin coincidencias retorna 200 con lista vacía."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, classroom=make_query([]))
        response = admin_client.get(f"{BASE_URL}/medical-cases/search?q=Inexistente")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["data"] == []
    assert body["data"]["total"] == 0


def test_get_medical_case_detail_success(admin_client):
    """Verifica detalle clínico de un caso médico junto con estudiante y contexto de salud."""
    case_row = {
        "id": 15,
        "student_id": 200,
        "doctor_id": 3,
        "type_of_case": "EMERGENCIA",
        "symptomatology": "Fiebre alta",
        "is_deleted": False
    }
    fake_student_detail = {
        "student": {"id": 200, "name": "Pedro", "lastname": "Pérez"},
        "representatives": [],
        "health_info": {"nutritional_status": "OPTIMO"}
    }
    doc_row = {
        "doc_id": 3,
        "user": {"id": 1, "name": "Roberto", "lastname": "Méndez"}
    }

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch.object(school_admin_service, "get_student_detail", return_value=fake_student_detail), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            medical_case=make_query([case_row]),
            doctor=make_query([doc_row])
        )
        response = admin_client.get(f"{BASE_URL}/medical-cases/15")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Detalle del caso médico obtenido exitosamente" in body["message"]
    data = body["data"]
    assert data["case_info"]["type_of_case"] == "EMERGENCIA"
    assert data["student_info"]["name"] == "Pedro"
    assert data["doctor_info"]["name"] == "Roberto"


def test_get_medical_case_detail_not_found_returns_404():
    """Caso médico inexistente -> 404."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, medical_case=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_medical_case_detail(user_id=4, case_id=999)

    assert exc.value.status_code == 404
    assert "No existe ningún caso médico" in exc.value.detail


def test_get_medical_case_detail_foreign_school_returns_403():
    """Caso médico cuyo estudiante pertenece a otra escuela -> 403 Forbidden."""
    case_row = {
        "id": 15,
        "student_id": 200,
        "is_deleted": False
    }
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch.object(school_admin_service, "get_student_detail",
                      side_effect=HTTPException(status_code=403, detail="pertenece a otra escuela")), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, medical_case=make_query([case_row]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_medical_case_detail(user_id=4, case_id=15)

    assert exc.value.status_code == 403
    assert "pertenece a otra escuela" in exc.value.detail


def test_get_medical_cases_tendency_monthly_success(admin_client):
    """Tendencia mensual de incidentes médicos agrupada con tasa de crecimiento."""
    fake_data = {
        "summary": {"total_incidents": 5, "growth_rate": 10.5},
        "data": [{"label": "Ene", "value": 2, "trend": 2.0}]
    }
    with patch.object(school_admin_service, "get_medical_cases_tendency", return_value=fake_data):
        response = admin_client.get(f"{BASE_URL}/students/medical-cases/tendency?mode=monthly&months=3")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["summary"]["total_incidents"] == 5


def test_get_medical_cases_tendency_weekly_success(admin_client):
    """Tendencia semanal de incidentes médicos."""
    fake_data = {
        "summary": {"total_incidents": 3, "growth_rate": 0.0},
        "data": [{"label": "Sem 10", "value": 1, "trend": 1.0}]
    }
    with patch.object(school_admin_service, "get_medical_cases_tendency", return_value=fake_data):
        response = admin_client.get(f"{BASE_URL}/students/medical-cases/tendency?mode=weekly&weeks=4")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


def test_get_medical_cases_tendency_empty(admin_client):
    """Sin aulas registradas retorna resumen con 0 incidentes y datos vacíos."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, classroom=make_query([]))
        response = admin_client.get(f"{BASE_URL}/students/medical-cases/tendency")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["summary"]["total_incidents"] == 0
    assert body["data"]["data"] == []


# ──────────────────────────────────────────────────────────
# 3. MÉTRICAS DE SALUD DE ESTUDIANTES
# ──────────────────────────────────────────────────────────

def test_get_student_metrics_history_success(admin_client):
    """Verifica respuesta 200 para historial de métricas corporales de un estudiante."""
    student_row = {"id": 10, "is_deleted": False}
    reg_row = {"classroom_id": 1}
    classroom_row = {"school_id": SCHOOL_ID}
    metrics_rows = [
        {"weight": 42.0, "height": 140.0, "updated_at": "2026-01-10T10:00:00Z"},
        {"weight": 40.0, "height": 138.0, "updated_at": "2025-10-10T10:00:00Z"}
    ]

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            student=make_query([student_row]),
            classroom_registration=make_query([reg_row]),
            classroom=make_query([classroom_row]),
            student_metrics=make_query(metrics_rows)
        )
        response = admin_client.get(f"{BASE_URL}/students/10/metrics?limit=10")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Historial de métricas obtenido exitosamente" in body["message"]
    data = body["data"]
    assert "peso" in data
    assert "altura" in data
    assert len(data["peso"]) == 2


def test_get_student_metrics_history_empty_metrics(admin_client):
    """Estudiante sin métricas registradas retorna 200 con data=None y mensaje descriptivo."""
    student_row = {"id": 10, "is_deleted": False}
    reg_row = {"classroom_id": 1}
    classroom_row = {"school_id": SCHOOL_ID}

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            student=make_query([student_row]),
            classroom_registration=make_query([reg_row]),
            classroom=make_query([classroom_row]),
            student_metrics=make_query([])  # Empty metrics
        )
        response = admin_client.get(f"{BASE_URL}/students/10/metrics")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] is None
    assert "no tiene métricas registradas" in body["message"]


def test_get_student_metrics_history_not_found_returns_404():
    """Estudiante inexistente -> 404."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, student=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_student_metrics_history(user_id=4, student_id=999, limit=10)

    assert exc.value.status_code == 404
    assert "No existe ningún estudiante" in exc.value.detail


def test_get_student_metrics_history_foreign_school_returns_403():
    """Estudiante de otra escuela -> 403 Forbidden."""
    student_row = {"id": 10, "is_deleted": False}
    reg_row = {"classroom_id": 99}
    classroom_row = {"school_id": OTHER_SCHOOL_ID}

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            student=make_query([student_row]),
            classroom_registration=make_query([reg_row]),
            classroom=make_query([classroom_row])
        )
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_student_metrics_history(user_id=4, student_id=10, limit=10)

    assert exc.value.status_code == 403
    assert "pertenece a otra escuela" in exc.value.detail


# ──────────────────────────────────────────────────────────
# 4. RBAC & Autenticación
# ──────────────────────────────────────────────────────────

def test_medical_unauthenticated_returns_401(client):
    """Sin credenciales -> 401."""
    response = client.get(f"{BASE_URL}/doctors")
    assert response.status_code == 401


def test_medical_invalid_jwt_returns_401(client):
    """Token malformado -> 401."""
    response = client.get(
        f"{BASE_URL}/doctors",
        headers={"Authorization": "Bearer jwt-invalido-xyz"}
    )
    assert response.status_code == 401


def test_medical_revoked_jwt_returns_401(client):
    """Token revocado -> 401."""
    token = create_access_token({"sub": "4", "role": "admin_escuela"})
    with patch.object(auth_service, "is_token_revoked", return_value=True):
        response = client.get(
            f"{BASE_URL}/doctors",
            headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 401


def test_medical_wrong_role_returns_403(client):
    """Rol no autorizado (ej. representante o doctor) -> 403 Forbidden."""
    app.dependency_overrides[get_current_user_token] = lambda: {
        "sub": "20",
        "role": "representante"
    }
    response = client.get(f"{BASE_URL}/doctors")
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False


def test_medical_admin_unlinked_returns_403(admin_client):
    """Administrador sin escuela vinculada -> 403 Forbidden."""
    with patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, school_administrator=make_query([]))
        response = admin_client.get(f"{BASE_URL}/doctors")

    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert "no está vinculado a ninguna escuela" in body["message"]


# ──────────────────────────────────────────────────────────
# 5. Validación de parámetros (422)
# ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("invalid_url", [
    f"{BASE_URL}/doctors/abc",                              # doctor_id not int
    f"{BASE_URL}/doctors?page=0",                           # page ge=1
    f"{BASE_URL}/doctors?size=500",                         # size le=100
    f"{BASE_URL}/medical-cases/abc",                        # case_id not int
    f"{BASE_URL}/medical-cases/search?date_from=invalid",   # date_from not date
    f"{BASE_URL}/students/medical-cases/tendency?months=0", # months ge=1
    f"{BASE_URL}/students/abc/metrics",                     # student_id not int
])
def test_medical_validation_errors(admin_client, invalid_url):
    """Parámetros no conformes devuelven 422 con formato estándar."""
    response = admin_client.get(invalid_url)
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
