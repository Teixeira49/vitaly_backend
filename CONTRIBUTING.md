# Guía de Contribución para Vitaly Backend

¡Gracias por interesarte en contribuir a Vitaly! Para mantener la calidad del proyecto y la agilidad en el desarrollo, seguimos estas directrices.

## 🚀 Configuración del Entorno de Desarrollo

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Teixeira49/vitaly_backend.git
   cd vitaly_backend
   ```

2. **Crear y activar un entorno virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Linux/Mac
   # venv\Scripts\activate  # En Windows
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Variables de Entorno:**
   Crea un archivo `.env` en la raíz basado en `.env.example` con las siguientes claves:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `JWT_SECRET`

5. **Ejecutar el servidor:**
   ```bash
   uvicorn app.main:app --reload
   ```

## 🏗️ Arquitectura y Estilo de Código

### Validación local y CI

Instala las herramientas de desarrollo y ejecuta los mismos controles que GitHub Actions:

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check app tests
python -m pytest -q
```

El workflow `.github/workflows/ci.yml` se ejecuta en cada pull request, al hacer
push a `development` o `main` y manualmente desde Actions. Usa Python 3.10, caché de pip y no
requiere secretos. Ruff comprueba inicialmente errores críticos (`E9`, `F63`,
`F7`, `F82`); ampliar las reglas de estilo queda como trabajo separado en #18.

Las pruebas ignoran el archivo `.env` y usan credenciales ficticias configuradas
en `tests/conftest.py`. Cada test debe simular sus llamadas a Supabase e ImageKit.
`pytest-socket` bloquea las conexiones de red; solo permite sockets Unix para el
bucle de eventos de `TestClient`. Las futuras pruebas de integración con servicios
reales deberán tener configuración y ejecución separadas.

Para impedir merges con controles fallidos, configura un ruleset o protección de
las ramas `development` y `main` en GitHub y exige el check **Lint and tests** después de su primera
ejecución. El archivo del workflow por sí solo no activa esa protección.

Seguimos una arquitectura de **capas** para separar responsabilidades. Por favor, mantén este orden:

*   **`app/api/`**: Solo define rutas y gestiona la entrada/salida de datos. Usa `deps.py` para la lógica de autenticación y protección por roles (RBAC).
*   **`app/services/`**: Toda la lógica de negocio y comunicación con Supabase debe residir aquí. Los servicios son consumidos por los endpoints.
*   **`app/schemas/`**: Usa Pydantic para validar todos los datos. Nunca devuelvas objetos crudos de la base de datos; usa esquemas de respuesta.
*   **`app/core/`**: Configuraciones globales y lógica del sistema (como la configuración de OpenAPI).

### Reglas de Oro:
- **Type Hints**: Es obligatorio usar tipado estático en todas las funciones.
- **Async**: Usa `async def` para operaciones de I/O de red siempre que sea posible.
- **PEP 8**: Sigue las convenciones estándar de estilo de Python.

## 🔐 Manejo de Base de Datos y Seguridad

*   **Supabase**: Accede a la base de datos siempre a través del cliente configurado en el proyecto.
*   **RBAC**: Antes de añadir un nuevo endpoint, verifica qué rol tiene acceso (`admin_sistema`, `admin_escuela` o `representante`) y aplica la dependencia correspondiente en `deps.py`.
*   **RLS**: Si realizas cambios en las tablas de Supabase, asegúrate de configurar las **Row Level Security policies** para proteger los datos a nivel de fila.

## 🌿 Flujo de Git y Commits

Adoptamos **Conventional Commits** para que el `CHANGELOG.md` se mantenga legible:

- `feat:` Una nueva funcionalidad.
- `fix:` Corrección de un error.
- `docs:` Cambios solo en la documentación.
- `refactor:` Un cambio de código que no corrige un error ni añade funcionalidad.
- `chore:` Actualización de dependencias o tareas de mantenimiento.

### Ramas (Branches):
- Actualiza `development` y crea la rama de trabajo desde ella usando
  `<tipo>/GH-<n>`; por ejemplo, `ci/GH-35`. Los hotfixes parten de `main`.
- Sigue `.agents/rules/branch-naming.md` para comprobar nombres disponibles y
  `.agents/rules/commit-conventions.md` para los commits con gitmoji.
- Las PR normales apuntan a `development`. Consulta `.claude/pr-config.json` y
  `.agents/rules/pull-request.md` antes de preparar o publicar una PR.

## 📄 Documentación

Si añades un endpoint o modificas un esquema:
1. Verifica que aparezca correctamente en `/docs` (Swagger UI).
2. Si el cambio es notable, añade una entrada en la sección `[Unreleased]` o en la última versión del `CHANGELOG.md`.

---
*Vitaly Backend Team - Automatizando el bienestar escolar.*
