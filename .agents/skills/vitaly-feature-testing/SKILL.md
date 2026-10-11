---
name: vitaly-feature-testing
description: Generates comprehensive pytest test suites for new FastAPI features in Vitaly. Covers APIResponse validation, multi-tenancy isolation (escuela_id), Supabase query mocking, empty table checks, and RBAC matrix. Use whenever creating or modifying endpoints, services, or features in the repo.
---

# Vitaly Feature Testing

Guía y generador de pruebas automatizadas con **pytest** y **FastAPI TestClient** adaptada a la arquitectura y estándares obligatorios de Vitaly Backend.

---

## Cuándo usar esta Skill

- Al implementar o modificar cualquier endpoint en `app/api/` o servicio en `app/services/`.
- Al generar la suite de tests unitarios o de integración en `tests/test_<feature>.py`.
- Al cumplir con la regla *"Keep tests with code"* exigida por `work-unit-commits` y `AGENTS.md`.
- Para validar seguridad multi-tenant, envelopes de respuesta y roles RBAC antes de abrir un PR.

---

## Las 5 Leyes del Testing en Vitaly

Todo conjunto de pruebas para una feature en Vitaly DEBE cubrir obligatoriamente estas 5 dimensiones:

| # | Dimensión | Regla Vitaly | Verificación en el Test |
|---|---|---|---|
| 1 | **Unified Envelope** | Todo endpoint retorna `APIResponse[T]` | `assert data["success"] is True`, `assert "data" in data`, `assert "message" in data` |
| 2 | **Multi-tenancy Silencioso** | Filtro obligatorio por `escuela_id` del token | Verificar que `.eq("escuela_id", current_user.escuela_id)` fue llamado y que datos de otra escuela no son expuestos. |
| 3 | **Mocking Determinista** | Tests autónomos sin llamadas de red vivas | Mockear `supabase.table().select().eq().execute()` con `MagicMock` y `patch`. |
| 4 | **Validación Tablas Vacías** | Prohibidos los errores 500 silenciosos | Cuando `data = []`, probar que retorne 404 limpio o lista vacía, nunca fallo de servidor. |
| 5 | **Matriz RBAC / Seguridad** | Control estricto con `RoleChecker` | Simular roles vía `app.dependency_overrides`: probar éxito con rol autorizado, 403 con rol inválido y 401 sin auth. |

---

## Matriz Estándar de Casos de Prueba (Por Feature)

Para cada nueva feature o conjunto de endpoints, genera un archivo en `tests/test_<feature>.py` con los siguientes casos mínimos:

### 1. `test_<feature>_success` (Happy Path)
- Configura mocks con datos válidos pertenecientes a la escuela del usuario autenticado.
- Ejecuta la petición (`client.get`, `post`, `put`, `delete`).
- Asevera status code (200 o 201).
- Valida la estructura `APIResponse(success=True, data=..., message=...)`.

### 2. `test_<feature>_tenant_isolation` (Aislamiento Multi-escuela)
- Simula una consulta donde existen registros de otra escuela (`escuela_id != current_user.escuela_id`).
- Verifica que el servicio o query filtre estrictamente por `current_user.escuela_id`.
- Confirma que el usuario no recibe datos de terceros (status 404 o `data: []`).

### 3. `test_<feature>_empty_or_not_found` (Tabla o Registro Inexistente)
- Configura el mock de Supabase para retornar `execute().data = []`.
- Verifica que el endpoint retorne `404 Not Found` (o lista vacía si es un listado) con mensaje amigable.
- Asegura que no ocurra un IndexError ni una excepción 500.

### 4. `test_<feature>_rbac_forbidden` (Control de Acceso)
- Inyecta un usuario con rol no autorizado en `app.dependency_overrides`.
- Ejecuta la petición.
- Verifica status `403 Forbidden` y detalle de denegación de permisos.

### 5. `test_<feature>_validation_error` (Esquemas Pydantic)
- Envía un payload con tipos incorrectos, valores faltantes o fuera de rango.
- Verifica status `422 Unprocessable Entity` generado por Pydantic.

---

## Plantilla Canónica de Test en Vitaly

```python
# tests/test_<feature>.py
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_user
# Importa la dependencia específica si aplica (ej. get_current_doctor, RoleChecker)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_user():
    return {
        "id": 10,
        "name": "Dra. Ana",
        "email": "ana@vitaly.app",
        "role": "doctor",
        "escuela_id": 1,
    }


def test_feature_success(client, mock_user):
    """Happy Path: Verifica retorno exitoso envuelto en APIResponse."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        with patch("app.services.<service_module>.supabase") as mock_supabase:
            mock_table = MagicMock()
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": 1, "escuela_id": 1, "nombre": "Registro Test"}]
            )

            response = client.get("/api/v1/<feature>/1")
            assert response.status_code == 200
            res_json = response.json()
            assert res_json["success"] is True
            assert res_json["data"]["id"] == 1
            assert "message" in res_json
    finally:
        app.dependency_overrides.clear()


def test_feature_tenant_isolation(client, mock_user):
    """Multi-tenancy: Verifica que no se acceda a datos de otra escuela."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        with patch("app.services.<service_module>.supabase") as mock_supabase:
            mock_table = MagicMock()
            mock_supabase.table.return_value = mock_table
            # Simula que para la escuela_id del usuario no hay datos
            mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )

            response = client.get("/api/v1/<feature>/999")
            assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_feature_rbac_forbidden(client):
    """RBAC: Verifica que un rol no autorizado reciba 403."""
    unauthorized_user = {"id": 2, "role": "representante", "escuela_id": 1}
    app.dependency_overrides[get_current_user] = lambda: unauthorized_user
    try:
        response = client.get("/api/v1/<feature>/1")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_feature_validation_error(client, mock_user):
    """Pydantic: Verifica que datos inválidos retornen 422."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = client.post("/api/v1/<feature>", json={"campo_invalido": 123})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
```

---

## Comandos de Ejecución

Para ejecutar la suite generada:

```bash
# Correr todos los tests del repositorio
pytest

# Correr los tests de una feature específica con reporte detallado
pytest tests/test_<feature>.py -v

# Correr tests con stop en primer fallo
pytest tests/test_<feature>.py -x
```
