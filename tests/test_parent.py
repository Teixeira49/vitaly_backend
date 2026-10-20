"""
Tests for Parent endpoints and service layer:
  - POST /api/v1/parent/link-students (link_authorized_students)

Adheres strictly to the 5 laws of vitaly-feature-testing:
  1. APIResponse envelope verification (success, data, message).
  2. Multi-tenancy and role security: strictly gated by get_current_representante.
  3. Deterministic supabase-py mock for user, parent, student and student_representative.
  4. Correct status codes: 404 for missing parent profile, 200 with empty list when no matches.
  5. RBAC matrix: 403 for unauthorized roles (admin_escuela, admin_sistema, doctor),
     401 for unauthenticated/revoked tokens.
"""
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc  # noqa: UP017
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.deps import get_current_representante
from app.core.security import create_access_token
from app.main import app
from app.services.parent_service import parent_service

ENDPOINT_MODULE = "app.api.v1.endpoints.parent"
SERVICE_MODULE = "app.services.parent_service"
PARENT_BASE_URL = "/api/v1/parent"


# ──────────────────────────────────────────────────────────
# Realistic JWT payload helpers
# ──────────────────────────────────────────────────────────

def parent_payload(user_id: int = 50) -> dict:
    """Claims for authenticated representante."""
    return {
        "sub": str(user_id),
        "email": "madre@vitaly.com",
        "role": "representante",
        "scope": "client",
        "name": "Ana López",
        "gender": "FEMENINO",
        "type_representative": "Madre",
    }


def admin_school_payload(user_id: int = 20) -> dict:
    """Claims for admin_escuela (unauthorized for parent endpoints)."""
    return {
        "sub": str(user_id),
        "email": "admin@vitaly.com",
        "role": "admin_escuela",
        "scope": "client",
        "name": "Laura Pérez",
        "gender": "FEMENINO",
    }


def doctor_payload(user_id: int = 30) -> dict:
    """Claims for doctor (unauthorized for parent endpoints)."""
    return {
        "sub": str(user_id),
        "email": "doctor@vitaly.com",
        "role": "doctor",
        "scope": "client",
        "name": "Roberto Sánchez",
        "gender": "MASCULINO",
    }


def sys_admin_payload(user_id: int = 10) -> dict:
    """Claims for admin_sistema (unauthorized for parent endpoints)."""
    return {
        "sub": str(user_id),
        "email": "sysadmin@vitaly.com",
        "role": "admin_sistema",
        "scope": "admin",
        "name": "Carlos Mendoza",
        "gender": "MASCULINO",
    }


# ──────────────────────────────────────────────────────────
# Chainable supabase-py mock helpers
# ──────────────────────────────────────────────────────────

def make_query(data=None, count=None) -> MagicMock:
    """Chainable mock for supabase-py queries."""
    query = MagicMock()
    for method in (
        "select", "eq", "neq", "in_", "is_", "ilike", "gte", "lte",
        "order", "range", "limit", "insert", "update", "delete", "or_", "contains"
    ):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=[] if data is None else data, count=count)
    return query


def route_tables(mock_supabase: MagicMock, **tables: MagicMock) -> None:
    """Route supabase.table(...) calls to table-specific query mocks."""
    mock_supabase.table.side_effect = lambda name: tables.get(name, make_query([]))


@pytest.fixture
def parent_client():
    """Client with get_current_representante dependency overridden."""
    app.dependency_overrides[get_current_representante] = lambda: parent_payload()
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
# 1. POST /link-students - Flujos Funcionales
# ──────────────────────────────────────────────────────────

class TestLinkStudentsFunctional:
    def test_link_students_success_new_and_already_linked(self, parent_client):
        """Vinculación exitosa de estudiantes autorizados con detección de ya vinculados."""
        user_query = make_query([{"identity_number": "V-12345678"}])
        parent_query = make_query([{"id": 7}])

        # Students found matching authorization_number
        students_found = [
            {"id": 101, "name": "Pedro", "lastname": "López"},
            {"id": 102, "name": "Lucía", "lastname": "López"},
        ]
        student_query = make_query(students_found)

        # student_representative checks:
        # First student 101: not linked yet (empty)
        # Second student 102: already linked
        def rep_table_side_effect():
            rep_mock = MagicMock()
            for method in ("select", "eq", "insert"):
                getattr(rep_mock, method).return_value = rep_mock

            # Alternate between not found (101) and found (102)
            call_count = {"count": 0}

            def execute_side_effect():
                call_count["count"] += 1
                if call_count["count"] == 1:
                    return MagicMock(data=[])  # student 101 not linked
                if call_count["count"] == 2:
                    return MagicMock(data=[{"id": 1}])  # student 101 insert
                return MagicMock(data=[{"id": 500}])  # student 102 check: found

            rep_mock.execute.side_effect = execute_side_effect
            return rep_mock

        rep_mock = rep_table_side_effect()

        with patch(f"{ENDPOINT_MODULE}.supabase") as mock_ep_sb, \
             patch(f"{SERVICE_MODULE}.supabase") as mock_svc_sb:
            route_tables(mock_ep_sb, user=user_query)
            route_tables(
                mock_svc_sb,
                parent=parent_query,
                student=student_query,
                student_representative=rep_mock,
            )

            response = parent_client.post(f"{PARENT_BASE_URL}/link-students")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "Se vincularon" in body["message"]
        assert len(body["data"]["linked_students"]) == 1
        assert body["data"]["linked_students"][0]["student_id"] == 101
        assert len(body["data"]["already_linked"]) == 1
        assert body["data"]["already_linked"][0]["student_id"] == 102

    def test_link_students_no_identity_in_profile_returns_200_with_message(self, parent_client):
        """Usuario sin número de identidad registrado -> 200 con data=None y mensaje explicativo."""
        user_query = make_query([{"identity_number": None}])

        with patch(f"{ENDPOINT_MODULE}.supabase") as mock_ep_sb:
            route_tables(mock_ep_sb, user=user_query)

            response = parent_client.post(f"{PARENT_BASE_URL}/link-students")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"] is None
        assert "No se encontró un número de identidad asociado a tu perfil" in body["message"]

    def test_link_students_no_authorized_students_found(self, parent_client):
        """No hay estudiantes autorizados con la cédula del representante -> 200 con lista vacía."""
        user_query = make_query([{"identity_number": "V-99999999"}])
        parent_query = make_query([{"id": 7}])
        student_query = make_query([])  # No matches

        with patch(f"{ENDPOINT_MODULE}.supabase") as mock_ep_sb, \
             patch(f"{SERVICE_MODULE}.supabase") as mock_svc_sb:
            route_tables(mock_ep_sb, user=user_query)
            route_tables(mock_svc_sb, parent=parent_query, student=student_query)

            response = parent_client.post(f"{PARENT_BASE_URL}/link-students")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["linked_students"] == []
        assert "No se encontraron estudiantes autorizados" in body["message"]

    def test_link_students_missing_parent_profile_returns_404(self, parent_client):
        """No existe registro en tabla parent para el user_id -> 404 Not Found."""
        user_query = make_query([{"identity_number": "V-12345678"}])
        parent_query = make_query([])  # No parent row

        with patch(f"{ENDPOINT_MODULE}.supabase") as mock_ep_sb, \
             patch(f"{SERVICE_MODULE}.supabase") as mock_svc_sb:
            route_tables(mock_ep_sb, user=user_query)
            route_tables(mock_svc_sb, parent=parent_query)

            response = parent_client.post(f"{PARENT_BASE_URL}/link-students")

        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert "No se encontró un perfil de representante asociado" in body["message"]


# ──────────────────────────────────────────────────────────
# 2. Matriz RBAC y Seguridad en /link-students
# ──────────────────────────────────────────────────────────

class TestLinkStudentsRBAC:
    def test_link_students_unauthenticated_returns_401_or_403(self, client):
        """Petición sin token -> 401/403."""
        response = client.post(f"{PARENT_BASE_URL}/link-students")
        assert response.status_code in (401, 403)

    def test_link_students_forbidden_for_admin_escuela(self, client):
        """Rol admin_escuela intentando invocar link-students -> 403 Forbidden."""
        token = create_access_token(data=admin_school_payload())
        with patch("app.services.auth_service.auth_service.is_token_revoked", return_value=False):
            response = client.post(
                f"{PARENT_BASE_URL}/link-students",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False
        assert "Se requiere rol de representante" in body["message"]

    def test_link_students_forbidden_for_doctor(self, client):
        """Rol doctor intentando invocar link-students -> 403 Forbidden."""
        token = create_access_token(data=doctor_payload())
        with patch("app.services.auth_service.auth_service.is_token_revoked", return_value=False):
            response = client.post(
                f"{PARENT_BASE_URL}/link-students",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False
        assert "Se requiere rol de representante" in body["message"]

    def test_link_students_forbidden_for_admin_sistema(self, client):
        """Rol admin_sistema intentando invocar link-students -> 403 Forbidden."""
        token = create_access_token(data=sys_admin_payload())
        with patch("app.services.auth_service.auth_service.is_token_revoked", return_value=False):
            response = client.post(
                f"{PARENT_BASE_URL}/link-students",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False
        assert "token emitido por el portal de clientes" in body["message"]

    def test_link_students_with_revoked_token_returns_401(self, client):
        """Token revocado previamente -> 401 Unauthorized."""
        token = create_access_token(data=parent_payload())
        with patch("app.services.auth_service.auth_service.is_token_revoked", return_value=True):
            response = client.post(
                f"{PARENT_BASE_URL}/link-students",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 401
        body = response.json()
        assert body["success"] is False
        assert "El token ha sido revocado" in body["message"]


# ──────────────────────────────────────────────────────────
# 3. Métodos del Servicio ParentService
# ──────────────────────────────────────────────────────────

class TestParentServiceDirect:
    def test_link_students_by_identity_direct_parent_not_found(self):
        """Invocación directa del servicio cuando no existe el perfil parent -> 404."""
        parent_query = make_query([])

        with patch(f"{SERVICE_MODULE}.supabase") as mock_sb:
            route_tables(mock_sb, parent=parent_query)

            with pytest.raises(HTTPException) as exc_info:
                parent_service.link_students_by_identity(user_id=99, identity_number="V-123")

            assert exc_info.value.status_code == 404
            assert "No se encontró un perfil de representante" in exc_info.value.detail
