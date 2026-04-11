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
- Crea ramas descriptivas: `feature/nombre-funcionalidad` o `fix/descripcion-bug`.

## 📄 Documentación

Si añades un endpoint o modificas un esquema:
1. Verifica que aparezca correctamente en `/docs` (Swagger UI).
2. Si el cambio es notable, añade una entrada en la sección `[Unreleased]` o en la última versión del `CHANGELOG.md`.

---
*Vitaly Backend Team - Automatizando el bienestar escolar.*
