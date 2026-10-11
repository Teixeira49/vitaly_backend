---
description: "Protocolo de orquestación End-to-End (E2E) y sincronización de contratos con el repositorio frontend hermano (vitaly-care-for-families)"
globs:
  - "app/api/**/*.py"
  - "app/schemas/**/*.py"
alwaysApply: false
---

# Protocolo de Orquestación E2E y Sincronización con Frontend

## 1. Scope & Context
- **Target Area:** Endpoints (`app/api/`), esquemas Pydantic (`app/schemas/`) y tareas completas End-to-End.
- **Repositorio Hermano:** El frontend reside en la ruta relativa `../vitaly-care-for-families` (Vite + React + TypeScript + TanStack Query).
- **Roles:** Backend Architect, Security Sentinel.
- **Objetivo:** Permitir la implementación coordinada de funcionalidades completas (E2E) asegurando la paridad de contratos entre FastAPI y el cliente frontend, sin filtrar rutas privadas locales.

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** incluyas rutas absolutas de tu máquina local (ej. `/Users/...` o `C:\...`) en código, documentación, `.env` o mensajes de commit.
- ⛔ **NUNCA** alteres o elimines campos en un esquema Pydantic (`*Read`, `*Create`) sin verificar o actualizar el DTO/interfaz correspondiente en el repositorio frontend hermano.
- ⛔ **NUNCA** mezcles cambios de ambos repositorios en un único commit. Cada repositorio mantiene su propio control de versiones e historial Git independiente.
- 🔒 **MANDATORIO:** Resuelve siempre la ubicación del frontend de forma relativa: `../vitaly-care-for-families` o `$(git rev-parse --show-toplevel)/../vitaly-care-for-families`.
- 🔒 **MANDATORIO:** Todo endpoint nuevo debe exponerse con el prefijo `/api/v1/` y responder con el formato unificado `APIResponse[T]`.

## 3. Directivas Prescriptivas para Tareas E2E

Cuando el usuario solicite implementar una funcionalidad End-to-End desde este repositorio:

1. **Fase 1: Autoridad de Datos (Backend Primero):**
   - Define o ajusta los modelos SQLAlchemy (`app/models/`).
   - Define los esquemas Pydantic (`*Create`, `*Update`, `*Read`) con `Field(description=...)`.
   - Crea el endpoint en `app/api/v1/` envuelto con `response_model=APIResponse[SchemaRead]` y asegurado con `Depends(RoleChecker(...))`.
2. **Fase 2: Verificación de Disponibilidad del Frontend:**
   - Comprueba si el directorio hermano existe de forma relativa:
     ```bash
     FRONTEND_DIR="$(git rev-parse --show-toplevel)/../vitaly-care-for-families"
     if [ -d "$FRONTEND_DIR" ]; then ... fi
     ```
3. **Fase 3: Sincronización de Tipos y Servicios en Frontend:**
   - Inspecciona o crea el servicio en `../vitaly-care-for-families/src/services/[feature]/[feature]Service.ts`.
   - Asegura que la interfaz TypeScript refleje el payload desempaquetado de `APIResponse.data`.
   - Agrega la llamada a `apiClient` con la ruta relativa exacta (ej. `/api/v1/...`).
4. **Fase 4: Consumo UI y Cláusulas de Guarda:**
   - Si se requiere actualizar vistas o hooks, valida que los componentes manejen el ciclo: `isLoading` -> `isError` -> `isEmpty` -> `Success`.

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
```bash
# Mal: Usar rutas absolutas de la máquina local o asumir que el frontend no existe
cd /Users/usuario/Desarrollo/proyecto/vitaly-care-for-families # ❌ Ruta privada expuesta
```

### ✅ Patrón Estándar (DO)
```bash
# Bien: Resolución dinámica y relativa basada en el árbol de trabajo
FRONTEND_PATH="$(git rev-parse --show-toplevel)/../vitaly-care-for-families"

if [ -d "$FRONTEND_PATH" ]; then
  echo "Repositorio frontend detectado en: $FRONTEND_PATH"
  # Proceder a verificar DTOs en $FRONTEND_PATH/src/services/...
fi
```

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] El endpoint de FastAPI funciona y pasa sus pruebas (`pytest tests/api/`).
  - [ ] Las interfaces TS en el frontend hermano coinciden con los campos de Pydantic.
  - [ ] Ninguna ruta absoluta del sistema de archivos fue escrita en el repositorio.
- **Comando de Verificación Backend:** `pytest tests/`
