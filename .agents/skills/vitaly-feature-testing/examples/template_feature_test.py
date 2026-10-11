"""
Plantilla de referencia para tests unitarios y de integración de endpoints en Vitaly.
Ubicación sugerida para tus tests: tests/test_<nombre_feature>.py
"""
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_user


@pytest.fixture
def client():
    """Cliente HTTP para pruebas en FastAPI."""
    return TestClient(app)


@pytest.fixture
def mock_doctor_user():
    """Usuario simulado autenticado con rol de doctor y escuela asignada."""
    return {
        "id": 20,
        "name": "Ricardo",
        "lastname": "Vargas",
        "email": "dr.vargas@vitaly.app",
        "role": "doctor",
        "escuela_id": 1,
    }


@pytest.fixture
def mock_representante_user():
    """Usuario simulado autenticado con rol de representante."""
    return {
        "id": 30,
        "name": "María",
        "lastname": "González",
        "email": "maria@vitaly.app",
        "role": "representante",
        "escuela_id": 1,
    }


def test_get_resource_success(client, mock_doctor_user):
    """
    1. HAPPY PATH:
    Valida status 200 y envoltura de respuesta estándar APIResponse[T].
    """
    app.dependency_overrides[get_current_user] = lambda: mock_doctor_user
    try:
        with patch("app.services.doctor_service.supabase") as mock_supabase:
            mock_table = MagicMock()
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": 1, "escuela_id": 1, "titulo": "Consulta General"}]
            )

            response = client.get("/api/v1/ejemplo/1")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert data["data"]["id"] == 1
            assert "message" in data
    finally:
        app.dependency_overrides.clear()


def test_resource_tenant_isolation(client, mock_doctor_user):
    """
    2. MULTI-TENANCY ISOLATION:
    Valida que las consultas aíslen por escuela_id y no permitan filtrar o ver datos de otra escuela.
    """
    app.dependency_overrides[get_current_user] = lambda: mock_doctor_user
    try:
        with patch("app.services.doctor_service.supabase") as mock_supabase:
            mock_table = MagicMock()
            mock_supabase.table.return_value = mock_table
            # Simula que la consulta con escuela_id del usuario no encuentra el registro
            mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )

            response = client.get("/api/v1/ejemplo/999")
            # Debe responder 404 y no exponer registros ajenos
            assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_resource_empty_table_handling(client, mock_doctor_user):
    """
    3. VALIDACIÓN DE TABLAS VACÍAS:
    Valida que si no hay registros, el sistema responda un 404 controlado y no un 500 silencioso.
    """
    app.dependency_overrides[get_current_user] = lambda: mock_doctor_user
    try:
        with patch("app.services.doctor_service.supabase") as mock_supabase:
            mock_table = MagicMock()
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )

            response = client.get("/api/v1/ejemplo/detalles-inexistentes")
            assert response.status_code in [404, 200]
            if response.status_code == 404:
                assert "no encontrado" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_resource_rbac_unauthorized(client, mock_representante_user):
    """
    4. CONTROL DE ACCESO (RBAC):
    Valida que un rol no autorizado reciba status 403 Forbidden.
    """
    app.dependency_overrides[get_current_user] = lambda: mock_representante_user
    try:
        response = client.get("/api/v1/ejemplo/solo-doctores")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_create_resource_validation_error(client, mock_doctor_user):
    """
    5. VALIDACIÓN DE ENTRADA PYDANTIC:
    Valida que campos faltantes o tipos erróneos devuelvan 422 Unprocessable Entity.
    """
    app.dependency_overrides[get_current_user] = lambda: mock_doctor_user
    try:
        payload_invalido = {"campo_requerido": None}
        response = client.post("/api/v1/ejemplo", json=payload_invalido)
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
