# Checklist de Calidad de Tests para Features en Vitaly

Antes de finalizar o abrir un Pull Request con una nueva feature, valida esta lista de verificación:

- [ ] **Ubicación:** El test reside en `tests/test_<feature>.py`.
- [ ] **Pytest Discovery:** El archivo es detectado automáticamente al ejecutar `pytest`.
- [ ] **Contrato APIResponse:** Todas las respuestas 200/201 verifican `response.json()["success"] is True` y el formato envelope (`data`, `message`).
- [ ] **Aislamiento Multi-tenancy:**
  - [ ] Se verifica que las consultas a la base de datos incluyan `escuela_id == current_user.escuela_id`.
  - [ ] Se verifica que un usuario de la Escuela A no pueda acceder a registros de la Escuela B.
- [ ] **Manejo de Tablas Vacías:**
  - [ ] Se simula que la consulta retorne lista vacía (`data = []`).
  - [ ] El sistema maneja el caso con `404 Not Found` (o lista vacía) sin generar excepciones `500` silenciosas.
- [ ] **Matriz de Seguridad (RBAC):**
  - [ ] Rol autorizado accede correctamente (`200 OK`).
  - [ ] Rol no autorizado recibe `403 Forbidden`.
  - [ ] Petición sin token recibe `401 Unauthorized`.
- [ ] **Validación Pydantic:**
  - [ ] Petición con esquema erróneo o campos requeridos faltantes retorna `422 Unprocessable Entity`.
- [ ] **Aislamiento de Red:**
  - [ ] Las dependencias externas (Supabase, servicios de correo, almacenamiento S3) están mockeadas con `unittest.mock.patch`.
  - [ ] Los tests se ejecutan de forma local y offline sin tocar bases de datos de producción.
