"""
Tests for School Admin Students endpoints and service layer:
  - GET /api/v1/school-admin/students/{student_id} (get_student_detail)
  - GET /api/v1/school-admin/representatives/{parent_id} (get_parent_detail)
  - PUT /api/v1/school-admin/students/{student_id} (update_student_profile)
  - GET /api/v1/school-admin/search/representatives (search_representatives)
  - PATCH /api/v1/school-admin/students/{student_id}/activate (activate_student)
  - PATCH /api/v1/school-admin/students/{student_id}/deactivate (deactivate_student)

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
# 1. GET /students/{student_id} (get_student_detail)
# ──────────────────────────────────────────────────────────

def test_get_student_detail_endpoint_success(admin_client):
    """Verifica respuesta 200 con envelope para detalle de estudiante."""
    fake_data = {
        "student": {
            "id": 10,
            "name": "Alejandro",
            "lastname": "Morales",
            "classroom_category": 1,
            "classroom_level": 2,
            "section": "A"
        },
        "representatives": [],
        "health_info": {
            "weight": 42.5,
            "height": 145.0,
            "bmi": 20.21,
            "nutritional_status": "OPTIMO"
        }
    }
    with patch.object(school_admin_service, "get_student_detail", return_value=fake_data) as mock_svc:
        response = admin_client.get(f"{BASE_URL}/students/10")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Detalle del estudiante obtenido exitosamente" in body["message"]
    assert body["data"]["student"]["name"] == "Alejandro"
    mock_svc.assert_called_once_with(user_id=4, student_id=10)


def test_get_student_detail_service_success():
    """Verifica lógica del servicio: validación de aula, representantes y métricas de salud."""
    student_row = {
        "id": 10,
        "name": "Alejandro",
        "lastname": "Morales",
        "birthday": "2014-03-15",
        "gender": "MASCULINO",
        "blood_type": "O+",
        "identity_number": "V-30111222",
        "is_active": True,
        "is_deleted": False
    }
    reg_row = {"classroom_id": 5}
    classroom_row = {
        "school_id": SCHOOL_ID,
        "category": 1,
        "level": 3,
        "section": "B"
    }
    sr_row = {"parent_id": 20}
    parent_row = {
        "id": 20,
        "user_id": 100,
        "occupation": "Ingeniero",
        "type_representative": "PADRE",
        "is_active": True
    }
    user_row = {
        "id": 100,
        "name": "María",
        "lastname": "Morales",
        "email": "maria@test.com",
        "gender": "FEMENINO",
        "address": "Calle 1"
    }
    metrics_row = {
        "weight": 45.0,
        "height": 150.0,
        "updated_at": "2026-01-15T10:00:00Z"
    }

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            student=make_query([student_row]),
            classroom_registration=make_query([reg_row]),
            classroom=make_query([classroom_row]),
            student_representative=make_query([sr_row]),
            parent=make_query([parent_row]),
            user=make_query([user_row]),
            student_metrics=make_query([metrics_row])
        )
        result = school_admin_service.get_student_detail(user_id=4, student_id=10)

    assert result["student"]["id"] == 10
    assert result["student"]["classroom_level"] == 3
    assert result["student"]["section"] == "B"
    # User info in representative
    reps = result["representatives"]
    assert len(reps) == 1
    assert reps[0]["user_info"]["name"] == "María"
    # Health info calculation
    # BMI: 45 / (1.5)^2 = 20.0 -> OPTIMO
    health = result["health_info"]
    assert health is not None
    assert health["nutritional_status"] == "OPTIMO"


def test_get_student_detail_not_found_returns_404():
    """Estudiante inexistente -> 404 Not Found."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, student=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_student_detail(user_id=4, student_id=999)

    assert exc.value.status_code == 404
    assert "No existe ningún estudiante" in exc.value.detail


def test_get_student_detail_not_registered_in_any_classroom_returns_403():
    """Estudiante sin inscripción en ningún salón -> 403 Forbidden."""
    student_row = {"id": 10, "name": "Sin Aula", "is_deleted": False}
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            student=make_query([student_row]),
            classroom_registration=make_query([])  # No registration
        )
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_student_detail(user_id=4, student_id=10)

    assert exc.value.status_code == 403
    assert "no está inscrito en ningún salón" in exc.value.detail


def test_get_student_detail_foreign_school_returns_403():
    """Estudiante en aula de otra escuela -> 403 Forbidden."""
    student_row = {"id": 10, "name": "Alumno", "is_deleted": False}
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
            school_admin_service.get_student_detail(user_id=4, student_id=10)

    assert exc.value.status_code == 403
    assert "pertenece a otra escuela" in exc.value.detail


# ──────────────────────────────────────────────────────────
# 2. GET /representatives/{parent_id} (get_parent_detail)
# ──────────────────────────────────────────────────────────

def test_get_parent_detail_endpoint_success(admin_client):
    """Verifica respuesta 200 con envelope para detalle de representante."""
    fake_data = {
        "representative_info": {"id": 20, "user": {"name": "Carlos"}},
        "children": [
            {
                "id": 10,
                "name": "Pedro Pérez",
                "bmi_status": "OPTIMO",
                "has_active_medical_case": False
            }
        ],
        "total_children": 1
    }
    with patch.object(school_admin_service, "get_parent_detail", return_value=fake_data):
        response = admin_client.get(f"{BASE_URL}/representatives/20")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Detalle del representante obtenido exitosamente" in body["message"]
    assert body["data"]["total_children"] == 1


def test_get_parent_detail_service_success():
    """Valida saneamiento de usuario del padre, cálculo de hijos y acceso por school_id."""
    parent_row = {
        "id": 20,
        "user_id": 50,
        "is_deleted": False,
        "user": {
            "name": "Roberto",
            "lastname": "Gómez",
            "password": "secret_password",
            "photo_file_id": "photo_id"
        }
    }
    sr_rows = [{"student_id": 10}]
    reg_rows = [{
        "student_id": 10,
        "classroom_id": 1,
        "classroom": {
            "school_id": SCHOOL_ID,
            "category": 1,
            "level": 2,
            "section": "A"
        }
    }]
    student_rows = [{
        "id": 10,
        "name": "Pedro",
        "lastname": "Gómez",
        "birthday": "2016-04-10"
    }]

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            parent=make_query([parent_row]),
            student_representative=make_query(sr_rows),
            classroom_registration=make_query(reg_rows),
            student=make_query(student_rows),
            medical_case=make_query([]),
            student_metrics=make_query([])
        )
        result = school_admin_service.get_parent_detail(user_id=4, parent_id=20)

    assert result["total_children"] == 1
    assert "password" not in result["representative_info"]["user"]
    assert "photo_file_id" not in result["representative_info"]["user"]
    assert result["children"][0]["name"] == "Pedro Gómez"


def test_get_parent_detail_not_found_returns_404():
    """Representante inexistente -> 404."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, parent=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_parent_detail(user_id=4, parent_id=999)

    assert exc.value.status_code == 404
    assert "No existe un representante" in exc.value.detail


def test_get_parent_detail_no_children_returns_403():
    """Representante sin hijos asociados -> 403."""
    parent_row = {"id": 20, "is_deleted": False, "user": {}}
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            parent=make_query([parent_row]),
            student_representative=make_query([])  # No children
        )
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_parent_detail(user_id=4, parent_id=20)

    assert exc.value.status_code == 403
    assert "no tiene estudiantes asociados" in exc.value.detail


def test_get_parent_detail_foreign_school_returns_403():
    """Representante cuyos hijos solo pertenecen a otra escuela -> 403."""
    parent_row = {"id": 20, "is_deleted": False, "user": {}}
    sr_rows = [{"student_id": 10}]
    reg_rows = [{
        "student_id": 10,
        "classroom_id": 99,
        "classroom": {"school_id": OTHER_SCHOOL_ID}
    }]

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            parent=make_query([parent_row]),
            student_representative=make_query(sr_rows),
            classroom_registration=make_query(reg_rows)
        )
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_parent_detail(user_id=4, parent_id=20)

    assert exc.value.status_code == 403
    assert "ninguno de sus hijos pertenece a tu escuela" in exc.value.detail


# ──────────────────────────────────────────────────────────
# 3. PUT /students/{student_id} (update_student_profile)
# ──────────────────────────────────────────────────────────

def test_update_student_profile_endpoint_success(admin_client):
    """Verifica actualización de estudiante vía PUT."""
    fake_data = {"student_id": 10, "updated": True}
    payload = {"name": "Carlos Actualizado", "lastname": "Pérez"}

    with patch.object(school_admin_service, "update_student_profile", return_value=fake_data):
        response = admin_client.put(f"{BASE_URL}/students/10", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["updated"] is True


def test_update_student_profile_service_success():
    """Valida actualización de campos de estudiante y reasignación de representante."""
    school_classrooms = [{"id": 1}, {"id": 2}]
    reg_rows = [{"id": 100}]  # Student is registered in classroom 1
    parent_rows = [{"id": 55}]
    curr_rep_rows = [{"id": 5}]

    student_query = make_query([{"id": 10}])
    rep_query = make_query(curr_rep_rows)

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            classroom=make_query(school_classrooms),
            classroom_registration=make_query(reg_rows),
            student=student_query,
            parent=make_query(parent_rows),
            student_representative=rep_query
        )
        result = school_admin_service.update_student_profile(
            user_id=4,
            student_id=10,
            payload={"name": "Nuevo Nombre", "representative_id": 55}
        )

    assert result["student_id"] == 10
    assert result["updated"] is True
    student_query.update.assert_called_once()
    rep_query.update.assert_called_once_with({"parent_id": 55})


def test_update_student_profile_foreign_school_returns_403():
    """Intento de actualizar un estudiante de otra escuela -> 403."""
    school_classrooms = [{"id": 1}]
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            classroom=make_query(school_classrooms),
            classroom_registration=make_query([])  # Student not in admin's school classrooms
        )
        with pytest.raises(HTTPException) as exc:
            school_admin_service.update_student_profile(
                user_id=4, student_id=10, payload={"name": "Nuevo"}
            )

    assert exc.value.status_code == 403
    assert "no está en su escuela" in exc.value.detail


def test_update_student_profile_invalid_representative_returns_400():
    """Asignación de un parent_id inexistente -> 400 Bad Request."""
    school_classrooms = [{"id": 1}]
    reg_rows = [{"id": 100}]

    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(
            mock_supabase,
            classroom=make_query(school_classrooms),
            classroom_registration=make_query(reg_rows),
            student=make_query([{"id": 10}]),
            parent=make_query([])  # Non-existent parent
        )
        with pytest.raises(HTTPException) as exc:
            school_admin_service.update_student_profile(
                user_id=4, student_id=10, payload={"representative_id": 9999}
            )

    assert exc.value.status_code == 400
    assert "parent_id" in exc.value.detail


# ──────────────────────────────────────────────────────────
# 4. GET /search/representatives (search_representatives)
# ──────────────────────────────────────────────────────────

def test_search_representatives_endpoint_success(admin_client):
    """Verifica buscador de representantes con paginación."""
    fake_data = {
        "data": [
            {
                "email": "padre@test.com",
                "name": "Juan",
                "lastname": "Pérez",
                "representative_id": 1,
                "user_id": 30,
                "ocupation": "Ingeniero"
            }
        ],
        "total": 1,
        "page": 1,
        "size": 20
    }
    with patch.object(school_admin_service, "search_representatives", return_value=fake_data):
        response = admin_client.get(f"{BASE_URL}/search/representatives?query=Juan&page=1&size=20")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] == 1
    assert body["data"]["data"][0]["name"] == "Juan"


def test_search_representatives_empty_query():
    """Búsqueda con término vacío retorna colección vacía con 200."""
    result = school_admin_service.search_representatives(query="   ", page=1, size=20)
    assert result["data"] == []
    assert result["total"] == 0


def test_search_representatives_no_match():
    """Sin coincidencias en la base de datos retorna data=[] con 200."""
    with patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, user=make_query([]))
        result = school_admin_service.search_representatives(query="Inexistente", page=1, size=20)

    assert result["data"] == []
    assert result["total"] == 0


# ──────────────────────────────────────────────────────────
# 5. PATCH /students/{student_id}/activate (activate_student)
# ──────────────────────────────────────────────────────────

def test_activate_student_endpoint_success(admin_client):
    """Verifica activación de estudiante."""
    fake_data = {"id": 10, "is_active": True}
    with patch.object(school_admin_service, "activate_student", return_value=fake_data):
        response = admin_client.patch(f"{BASE_URL}/students/10/activate")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Estudiante activado exitosamente" in body["message"]
    assert body["data"]["is_active"] is True


def test_activate_student_not_found_returns_404():
    """Estudiante inexistente -> 404."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, student=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.activate_student(user_id=4, student_id=999)

    assert exc.value.status_code == 404
    assert "Estudiante no encontrado" in exc.value.detail


def test_activate_student_already_deleted_returns_400():
    """No se puede activar a un alumno eliminado (is_deleted=True) -> 400."""
    student_row = {"id": 10, "is_active": False, "is_deleted": True}
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, student=make_query([student_row]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.activate_student(user_id=4, student_id=10)

    assert exc.value.status_code == 400
    assert "eliminado" in exc.value.detail


def test_activate_student_foreign_school_returns_403():
    """No se puede activar a un alumno de otra escuela -> 403."""
    student_row = {"id": 10, "is_active": False, "is_deleted": False}
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
            school_admin_service.activate_student(user_id=4, student_id=10)

    assert exc.value.status_code == 403
    assert "pertenece a otra escuela" in exc.value.detail


# ──────────────────────────────────────────────────────────
# 6. PATCH /students/{student_id}/deactivate (deactivate_student)
# ──────────────────────────────────────────────────────────

def test_deactivate_student_endpoint_success(admin_client):
    """Verifica desactivación de estudiante."""
    fake_data = {"id": 10, "is_active": False}
    with patch.object(school_admin_service, "deactivate_student", return_value=fake_data):
        response = admin_client.patch(f"{BASE_URL}/students/10/deactivate")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Estudiante desactivado exitosamente" in body["message"]
    assert body["data"]["is_active"] is False


def test_deactivate_student_not_found_returns_404():
    """Estudiante inexistente -> 404."""
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, student=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.deactivate_student(user_id=4, student_id=999)

    assert exc.value.status_code == 404
    assert "Estudiante no encontrado" in exc.value.detail


def test_deactivate_student_foreign_school_returns_403():
    """No se puede desactivar a un alumno de otra escuela -> 403."""
    student_row = {"id": 10, "is_active": True, "is_deleted": False}
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
            school_admin_service.deactivate_student(user_id=4, student_id=10)

    assert exc.value.status_code == 403
    assert "pertenece a otra escuela" in exc.value.detail


# ──────────────────────────────────────────────────────────
# 7. RBAC & Autenticación
# ──────────────────────────────────────────────────────────

def test_students_unauthenticated_returns_401(client):
    """Sin credenciales -> 401."""
    response = client.get(f"{BASE_URL}/students/10")
    assert response.status_code == 401


def test_students_invalid_jwt_returns_401(client):
    """Token malformado -> 401."""
    response = client.get(
        f"{BASE_URL}/students/10",
        headers={"Authorization": "Bearer jwt-invalido"}
    )
    assert response.status_code == 401


def test_students_revoked_jwt_returns_401(client):
    """Token revocado -> 401."""
    token = create_access_token({"sub": "4", "role": "admin_escuela"})
    with patch.object(auth_service, "is_token_revoked", return_value=True):
        response = client.get(
            f"{BASE_URL}/students/10",
            headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 401


def test_students_wrong_role_returns_403(client):
    """Rol no autorizado (ej. doctor) -> 403 Forbidden."""
    app.dependency_overrides[get_current_user_token] = lambda: {
        "sub": "20",
        "role": "doctor"
    }
    response = client.get(f"{BASE_URL}/students/10")
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False


# ──────────────────────────────────────────────────────────
# 8. Validación de parámetros (422)
# ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("invalid_url", [
    f"{BASE_URL}/students/abc",                 # student_id not int
    f"{BASE_URL}/representatives/abc",          # parent_id not int
    f"{BASE_URL}/search/representatives",       # missing query parameter
    f"{BASE_URL}/search/representatives?query=test&page=0",  # page ge=1
    f"{BASE_URL}/search/representatives?query=test&size=500",  # size le=100
])
def test_students_validation_errors(admin_client, invalid_url):
    """Parámetros no conformes devuelven 422 con formato estándar."""
    response = admin_client.get(invalid_url)
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
