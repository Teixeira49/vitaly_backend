"""
Tests for Academic Year and Public Catalogs endpoints:
  - POST /api/v1/academic-year (create_academic_year)
  - PATCH /api/v1/academic-year/sync-current (sync_current_academic_years)
  - GET /api/v1/catalogs/states (get_states)
  - GET /api/v1/catalogs/school-types (get_school_types)
  - GET /api/v1/catalogs/classroom-categories (get_classroom_categories)
  - GET /api/v1/catalogs/system-status (get_system_status)

Adheres strictly to the 5 laws of vitaly-feature-testing:
  1. APIResponse envelope verification (success, data, message).
  2. Public accessibility: no JWT required (# PUBLIC_ROUTE).
  3. Deterministic supabase-py mock.
  4. Status codes and business logic: 400 for inverted date ranges, 200 with count for sync.
  5. Validation: 422 for malformed dates.
"""
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc  # noqa: UP017
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

ACADEMIC_YEAR_MODULE = "app.api.v1.endpoints.academic_year"
CATALOGS_MODULE = "app.api.v1.endpoints.catalogs"
AY_BASE_URL = "/api/v1/academic-year"
CATALOGS_BASE_URL = "/api/v1/catalogs"


# ──────────────────────────────────────────────────────────
# Mock Helpers
# ──────────────────────────────────────────────────────────

def make_query(data=None, count=None) -> MagicMock:
    query = MagicMock()
    for method in (
        "select", "eq", "neq", "in_", "is_", "ilike", "gte", "lte",
        "order", "range", "limit", "insert", "update", "delete", "or_"
    ):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=[] if data is None else data, count=count)
    return query


def route_tables(mock_supabase: MagicMock, **tables: MagicMock) -> None:
    mock_supabase.table.side_effect = lambda name: tables.get(name, make_query([]))


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────
# 1. POST /academic-year - Creación de Año Académico
# ──────────────────────────────────────────────────────────

class TestCreateAcademicYear:
    def test_create_academic_year_success_current(self, client):
        """Creación exitosa de año académico que abarca la fecha actual (is_current=True)."""
        today = date.today()
        start = today - timedelta(days=60)
        end = today + timedelta(days=200)

        ay_insert = make_query([{
            "id": 1,
            "name": f"Año escolar {start.year}-{end.year}",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "is_current": True,
            "is_active": True,
            "is_deleted": False,
        }])

        with patch(f"{ACADEMIC_YEAR_MODULE}.supabase") as mock_sb:
            route_tables(mock_sb, academic_year=ay_insert)

            payload = {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            }
            response = client.post(f"{AY_BASE_URL}", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Año académico creado exitosamente"
        assert body["data"]["is_current"] is True
        assert body["data"]["name"] == f"Año escolar {start.year}-{end.year}"

    def test_create_academic_year_inverted_dates_returns_400(self, client):
        """Fecha de inicio mayor o igual a fecha de fin -> 400 Bad Request."""
        payload = {
            "start_date": "2026-09-01",
            "end_date": "2026-06-01",
        }
        response = client.post(f"{AY_BASE_URL}", json=payload)
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert "La fecha de inicio debe ser menor a la fecha de cierre" in body["message"]

    def test_create_academic_year_database_error_returns_500(self, client):
        """Fallo en base de datos al insertar -> 500 Internal Server Error."""
        ay_empty = make_query([])  # Empty data returned from insert

        with patch(f"{ACADEMIC_YEAR_MODULE}.supabase") as mock_sb:
            route_tables(mock_sb, academic_year=ay_empty)

            payload = {
                "start_date": "2025-09-01",
                "end_date": "2026-07-31",
            }
            response = client.post(f"{AY_BASE_URL}", json=payload)

        assert response.status_code == 500
        body = response.json()
        assert body["success"] is False

    def test_create_academic_year_invalid_date_format_returns_422(self, client):
        """Formato de fecha inválido -> 422 Unprocessable Entity."""
        payload = {
            "start_date": "invalid-date",
            "end_date": "2026-07-31",
        }
        response = client.post(f"{AY_BASE_URL}", json=payload)
        assert response.status_code == 422


# ──────────────────────────────────────────────────────────
# 2. PATCH /academic-year/sync-current - Sincronización
# ──────────────────────────────────────────────────────────

class TestSyncCurrentAcademicYears:
    def test_sync_current_academic_years_updates_outdated(self, client):
        """Sincroniza y actualiza años cuyo is_current no coincidía con el calendario."""
        today = date.today()
        current_year_record = {
            "id": 1,
            "start_date": (today - timedelta(days=30)).isoformat(),
            "end_date": (today + timedelta(days=150)).isoformat(),
            "is_current": False,  # Outdated, should be True
        }
        old_year_record = {
            "id": 2,
            "start_date": (today - timedelta(days=400)).isoformat(),
            "end_date": (today - timedelta(days=100)).isoformat(),
            "is_current": True,  # Outdated, should be False
        }

        ay_query = make_query([current_year_record, old_year_record])

        with patch(f"{ACADEMIC_YEAR_MODULE}.supabase") as mock_sb:
            route_tables(mock_sb, academic_year=ay_query)

            response = client.patch(f"{AY_BASE_URL}/sync-current")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "Sincronización de años académicos completada" in body["message"]
        assert body["data"]["updated_records"] == 2
        assert body["data"]["current_date"] == today.isoformat()

    def test_sync_current_academic_years_empty_records(self, client):
        """Sin años académicos registrados -> 200 con 0 registros actualizados."""
        ay_empty = make_query([])

        with patch(f"{ACADEMIC_YEAR_MODULE}.supabase") as mock_sb:
            route_tables(mock_sb, academic_year=ay_empty)

            response = client.patch(f"{AY_BASE_URL}/sync-current")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["updated_records"] == 0
        assert "No se encontraron registros de años académicos" in body["message"]


# ──────────────────────────────────────────────────────────
# 3. Catálogos Públicos (/catalogs)
# ──────────────────────────────────────────────────────────

class TestPublicCatalogs:
    def test_get_states_public(self, client):
        """Catálogo público de estados disponible sin autenticación."""
        states_data = [
            {"id": 1, "name": "Distrito Capital"},
            {"id": 2, "name": "Miranda"},
        ]
        states_query = make_query(states_data)

        with patch(f"{CATALOGS_MODULE}.supabase") as mock_sb:
            route_tables(mock_sb, states=states_query)
            response = client.get(f"{CATALOGS_BASE_URL}/states")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Estados obtenidos exitosamente"
        assert len(body["data"]) == 2
        assert body["data"][0]["name"] == "Distrito Capital"

    def test_get_school_types_public(self, client):
        """Catálogo público de tipos de escuela disponible sin autenticación."""
        types_data = [
            {"id": 1, "name": "Pública"},
            {"id": 2, "name": "Privada"},
        ]
        types_query = make_query(types_data)

        with patch(f"{CATALOGS_MODULE}.supabase") as mock_sb:
            route_tables(mock_sb, school_type=types_query)
            response = client.get(f"{CATALOGS_BASE_URL}/school-types")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Tipos de escuela obtenidos exitosamente"
        assert len(body["data"]) == 2

    def test_get_classroom_categories_public(self, client):
        """Catálogo público de categorías de salón disponible sin autenticación."""
        categories_data = [
            {"id": 1, "name": "Preescolar"},
            {"id": 2, "name": "Primaria"},
            {"id": 3, "name": "Bachillerato"},
        ]
        cat_query = make_query(categories_data)

        with patch(f"{CATALOGS_MODULE}.supabase") as mock_sb:
            route_tables(mock_sb, classroom_category=cat_query)
            response = client.get(f"{CATALOGS_BASE_URL}/classroom-categories")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Categorías de salón obtenidas exitosamente"
        assert len(body["data"]) == 3

    def test_get_system_status_public(self, client):
        """Catálogo público de estatus de sistema disponible sin autenticación."""
        status_data = [
            {"id": 1, "name": "Activo"},
            {"id": 2, "name": "Pendiente"},
            {"id": 3, "name": "Inactivo"},
        ]
        status_query = make_query(status_data)

        with patch(f"{CATALOGS_MODULE}.supabase") as mock_sb:
            route_tables(mock_sb, system_status=status_query)
            response = client.get(f"{CATALOGS_BASE_URL}/system-status")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Estatus de sistema obtenidos exitosamente"
        assert len(body["data"]) == 3
