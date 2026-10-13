"""
Reference test suite for a Vitaly feature, written against a REAL endpoint so it imports and
runs as-is: GET /api/v1/school-admin/classrooms/{classroom_id}/students
(app/api/v1/endpoints/school_admin_classrooms.py -> SchoolAdminService.get_students_by_classroom).

Copy it to tests/test_<feature>.py and adapt the route, service and tables.

Layers covered:
  - Endpoint (TestClient): envelope, RBAC matrix (403 / 401), 422, status codes.
  - Service (direct call): tenant filter, 403 foreign school, 404 missing row, [] empty list.
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
URL = "/api/v1/school-admin/classrooms/{classroom_id}/students"
SCHOOL_ID = 1
OTHER_SCHOOL_ID = 2


# ──────────────────────────────────────────────────────────
# Helpers: realistic JWT payloads and a chainable supabase-py mock
# ──────────────────────────────────────────────────────────

def admin_payload(user_id: int = 4) -> dict:
    """Same claims auth_service.login puts in the token for admin_escuela (no school_id claim)."""
    return {
        "sub": str(user_id),
        "email": "admin@colegio.test",
        "role": "admin_escuela",
        "name": "Laura Pérez",
        "gender": "FEMENINO",
        "administrative_position": "Coordinadora",
        "school": "Colegio San Ignacio",
    }


def make_query(data=None, count=None) -> MagicMock:
    """A supabase-py query builder mock: every builder method returns itself,
    so any chain (.select().eq().eq().range()...) ends in the same .execute()."""
    query = MagicMock()
    for method in ("select", "eq", "neq", "in_", "is_", "ilike", "gte", "lte",
                   "order", "range", "limit", "insert", "update", "delete"):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=[] if data is None else data, count=count)
    return query


def route_tables(mock_supabase: MagicMock, **tables: MagicMock) -> None:
    """Dispatch supabase.table(<name>) to a per-table query mock. Unknown tables fail loudly."""
    mock_supabase.table.side_effect = lambda name: tables[name]


# ──────────────────────────────────────────────────────────
# Fixtures (aligned with tests/test_profile_photo.py::admin_client)
# ──────────────────────────────────────────────────────────

@pytest.fixture
def admin_client():
    """Authenticated admin_escuela: overrides the role gate the endpoint depends on."""
    app.dependency_overrides[get_current_admin_escuela] = lambda: admin_payload()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client():
    """No overrides: the real HTTPBearer + JWT decode + role gate run."""
    app.dependency_overrides.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────
# 1. Happy path + APIResponse envelope (endpoint layer)
# ──────────────────────────────────────────────────────────

def test_get_students_by_classroom_success(admin_client):
    result = {"classroom": {"id": 7, "school_id": SCHOOL_ID}, "data": [{"id": 1}],
              "total": 1, "page": 1, "size": 20}
    with patch.object(school_admin_service, "get_students_by_classroom",
                      return_value=result) as service_call:
        response = admin_client.get(URL.format(classroom_id=7))

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["data"] == [{"id": 1}]   # legacy: pagination nested inside data
    # New paginated endpoints: assert body["data"] is the list and body["meta"] carries
    # PaginationMeta (page, size, total, total_pages; app/schemas/responses.py).
    assert body["message"]
    # user_id comes from the token `sub`, never from the client
    service_call.assert_called_once_with(user_id=4, classroom_id=7, page=1, size=20)


# ──────────────────────────────────────────────────────────
# 2. Tenant isolation (service layer, supabase mocked)
# ──────────────────────────────────────────────────────────

def test_tenant_school_id_resolved_server_side_and_used():
    classroom = make_query([{"id": 7, "school_id": SCHOOL_ID, "category": 2, "level": 1,
                             "section": "A", "academic_year_id": 3}])
    registrations = make_query([{"student_id": 1}], count=1)
    students = make_query([{"id": 1, "name": "Ana"}])
    with patch.object(school_admin_service, "_get_school_id_for_admin",
                      return_value=SCHOOL_ID) as resolve, \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, classroom=classroom, classroom_registration=registrations,
                     student=students, medical_case=make_query([]),
                     student_metrics=make_query([]))
        result = school_admin_service.get_students_by_classroom(
            user_id=4, classroom_id=7, page=1, size=20)

    resolve.assert_called_once_with(4)
    assert result["total"] == 1
    # For a query scoped directly by tenant, assert the filter instead:
    #   tables["classroom"].eq.assert_any_call("school_id", SCHOOL_ID)


def test_tenant_foreign_school_row_returns_403():
    """Standard: a row that exists but belongs to another school -> 403 (not 404)."""
    classroom = make_query([{"id": 7, "school_id": OTHER_SCHOOL_ID}])
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, classroom=classroom)
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_students_by_classroom(
                user_id=4, classroom_id=7, page=1, size=20)

    assert exc.value.status_code == 403


def test_admin_not_linked_to_any_school_returns_403():
    """_get_school_id_for_admin itself: no school_administrator row -> 403."""
    with patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, school_administrator=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service._get_school_id_for_admin(4)

    assert exc.value.status_code == 403


# ──────────────────────────────────────────────────────────
# 3. Missing single resource -> 404 / empty collection -> 200 + []
# ──────────────────────────────────────────────────────────

def test_missing_classroom_returns_404():
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, classroom=make_query([]))
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_students_by_classroom(
                user_id=4, classroom_id=999, page=1, size=20)

    assert exc.value.status_code == 404


@pytest.mark.xfail(strict=True, reason="Legacy: service raises 404 on an empty classroom; "
                   "rule empty-table-validation requires 200 + data=[]. Remove when fixed.")
def test_empty_classroom_returns_empty_list():
    classroom = make_query([{"id": 7, "school_id": SCHOOL_ID}])
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=SCHOOL_ID), \
         patch(f"{SERVICE_MODULE}.supabase") as mock_supabase:
        route_tables(mock_supabase, classroom=classroom,
                     classroom_registration=make_query([], count=0))
        result = school_admin_service.get_students_by_classroom(
            user_id=4, classroom_id=7, page=1, size=20)

    assert result["data"] == []
    assert result["total"] == 0


def test_http_error_body_uses_envelope(admin_client):
    """Global handler (app/core/exceptions.py) turns HTTPException into APIResponse:
    the client gets `message`, not FastAPI's default `detail`."""
    with patch.object(school_admin_service, "get_students_by_classroom",
                      side_effect=HTTPException(status_code=404, detail="No existe ningún salón con ID 999.")):
        response = admin_client.get(URL.format(classroom_id=999))

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert "No existe" in body["message"]


# ──────────────────────────────────────────────────────────
# 4. RBAC matrix (real gate runs; only the token layer is faked)
# ──────────────────────────────────────────────────────────

def test_wrong_role_returns_403(client):
    # Override the token decoder, NOT the role gate, so get_current_admin_escuela really runs.
    app.dependency_overrides[get_current_user_token] = lambda: {"sub": "30", "role": "representante"}
    response = client.get(URL.format(classroom_id=7))

    assert response.status_code == 403
    assert response.json()["success"] is False


def test_invalid_token_returns_401(client):
    response = client.get(URL.format(classroom_id=7),
                          headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_revoked_token_returns_401(client):
    token = create_access_token({"sub": "4", "role": "admin_escuela"})
    with patch.object(auth_service, "is_token_revoked", return_value=True):
        response = client.get(URL.format(classroom_id=7),
                              headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_missing_token_is_rejected(client):
    # 401 guaranteed by the pinned fastapi[standard]>=0.122.0: security classes such as
    # HTTPBearer return 401 on missing credentials since 0.122.0.
    response = client.get(URL.format(classroom_id=7))
    assert response.status_code == 401


# ──────────────────────────────────────────────────────────
# 5. Validation (422 with envelope)
# ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    URL.format(classroom_id="abc"),            # path param not an int
    URL.format(classroom_id=7) + "?page=0",    # Query(ge=1)
    URL.format(classroom_id=7) + "?size=500",  # Query(le=100)
])
def test_invalid_input_returns_422(admin_client, path):
    response = admin_client.get(path)

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["errors"]
