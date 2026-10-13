---
title: "[🔒 Seguridad] POST /academic-year y PATCH /academic-year/sync-current no requieren autenticación"
labels: [security, bug, P0, api]
issue: 14
url: https://github.com/Teixeira49/vitaly_backend/issues/14
---

## Descripción

Los dos endpoints del módulo de año académico mutan datos globales de la plataforma y no exigen ningún token ni rol. El router no declara dependencias, ninguna de las funciones inyecta un gate de `app/api/deps.py` y los docstrings lo declaran explícitamente ("No requiere JWT"). Tampoco llevan el marcador `# PUBLIC_ROUTE`, por lo que no son rutas públicas documentadas: son rutas sin proteger.

## Evidencia

- `app/api/v1/endpoints/academic_year.py:7` — `router = APIRouter()` sin `dependencies=[...]`.
- `app/api/v1/endpoints/academic_year.py:9-10` — `@router.post("")` / `def create_academic_year(payload: AcademicYearCreate)`: sin `Depends(get_current_*)`.
- `app/api/v1/endpoints/academic_year.py:15` — docstring: "No requiere protección con JWT."
- `app/api/v1/endpoints/academic_year.py:43-44` — `@router.patch("/sync-current")` / `def sync_current_academic_years()`: sin parámetros ni dependencias.
- `app/api/v1/endpoints/academic_year.py:49` — docstring: "No requiere JWT."
- `app/api/v1/endpoints/academic_year.py:35` y `:80` — escriben directamente en la tabla `academic_year` (insert / update de `is_current`).
- `app/api/v1/router.py:11` — montado en `/api/v1/academic-year` sin dependencias a nivel de `include_router`.
- Verificación: `grep -n "Depends" app/api/v1/endpoints/academic_year.py` no devuelve resultados.

## Comportamiento actual vs esperado

- **Actual:** cualquier cliente sin token puede invocar ambos endpoints; FastAPI no exige el header `Authorization`.
- **Esperado:** las rutas que mutan datos exigen un gate de rol (`.agents/rules/rbac-enforcement.md`); sin token → 401, rol incorrecto → 403.

## Impacto

- ¿Expone datos médicos/PHR o PII? No directamente.
- ¿Fuga entre escuelas (`school_id`)? Es un problema de integridad **cross-tenant**: `academic_year` es global y `is_current` es el discriminador de "año vigente" que consumen los listados de salones, dashboards y filtros médicos de **todas** las escuelas. Un año insertado o resincronizado por un tercero cambia silenciosamente lo que ve cada escuela.
- Roles afectados: todos (el efecto alcanza a `admin_escuela`, `doctor` y `representante` de toda la plataforma).
- Nota: según #5, hoy ambos endpoints fallan con 500 por desalineación de columnas con el esquema real; la vulnerabilidad se vuelve explotable en cuanto se corrija ese esquema, por lo que ambos cambios deben ir juntos.

## Propuesta de solución

1. Proteger ambos endpoints con un gate de `app/api/deps.py`, ya sea por endpoint (`admin_payload: dict = Depends(...)`) o a nivel de router (`APIRouter(dependencies=[Depends(...)])`).
2. Eliminar del docstring las frases "No requiere JWT".

**Decisión abierta:** ¿qué gate corresponde? La opción probable es `get_current_admin_sistema` (el año académico es un recurso global de plataforma, coherente con #5). ¿Debe `sync-current` ser invocable también por un proceso programado (cron) con otra credencial, o solo por `admin_sistema`?

## Criterios de aceptación

- [ ] `POST /api/v1/academic-year` sin token responde 401 con envelope `APIResponse`.
- [ ] `PATCH /api/v1/academic-year/sync-current` sin token responde 401.
- [ ] Ambos responden 403 con un token de rol distinto al gate elegido.
- [ ] Ambos funcionan con un token del rol autorizado.
- [ ] Tests en `tests/` cubren 401/403/200 para ambos endpoints (skill `vitaly-feature-testing`).
- [ ] Los docstrings ya no dicen "No requiere JWT".

## Referencias

- `.agents/rules/rbac-enforcement.md`
- Skill `vitaly-rbac` (sección "Known rule drift" ya marca este gap)
- Relacionado con #5 (Fase 0 — reparar `academic_year`; su tarea "Proteger ambos endpoints")
