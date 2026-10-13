---
title: "[♻️ Deuda técnica] Rutas públicas sin marcador # PUBLIC_ROUTE y test de guardia de rutas inexistente"
labels: [tech-debt, P2, api]
issue: 17
url: https://github.com/Teixeira49/vitaly_backend/issues/17
---

## Descripción

La regla RBAC exige que toda ruta pública lleve el comentario `# PUBLIC_ROUTE` justo encima de la función, para distinguir "pública a propósito" de "olvidé el gate". Hoy ninguna ruta lo cumple: en `catalogs.py` el marcador está dentro del docstring, y el resto de rutas públicas no tiene marcador. Tampoco existe el test de guardia que debería fallar ante cualquier ruta sin gate ni marcador, por lo que gaps como el de `academic_year` no se detectan automáticamente.

## Evidencia

Marcador en el lugar incorrecto (dentro del docstring):

- `app/api/v1/endpoints/catalogs.py:13`, `:22`, `:31`, `:40` — `No requiere protección JWT. # PUBLIC_ROUTE` dentro del docstring de `get_states`, `get_school_types`, `get_classroom_categories`, `get_system_status`.

Rutas públicas sin marcador:

- `app/api/v1/endpoints/auth.py:10-11` `register_system_admin`, `:18-19` `register_school_admin`, `:27-28` `register_doctor`, `:36-37` `register_parent`, `:45-46` `login`.
- `app/api/v1/endpoints/school.py:9-10` — `GET /api/v1/schools` (`get_schools`).
- `app/main.py:51-52` `/`, `:55-56` `/health`, `:72-73` `/health-visual`.

Test de guardia inexistente:

- `tests/` solo contiene `test_doctor_profile.py` y `test_profile_photo.py`; no existe `tests/api/test_route_protection.py`.
- El test está especificado en `.agents/skills/vitaly-rbac/SKILL.md:90-121` y la regla lo menciona como pendiente (`.agents/rules/rbac-enforcement.md:88`).
- Reproducción: `grep -rn "PUBLIC_ROUTE" app/` solo devuelve las 4 líneas de docstring de `catalogs.py`.

## Comportamiento actual vs esperado

- **Actual:** no se puede distinguir por inspección ni por test qué rutas son públicas intencionalmente; una ruta nueva sin gate pasa revisión y CI sin aviso.
- **Esperado:** `# PUBLIC_ROUTE` como comentario encima de cada función pública (`.agents/rules/rbac-enforcement.md:20`) y un test que falla si alguna ruta no tiene gate (`get_current_user_token` en su árbol de dependencias) ni marcador.

## Impacto

- ¿Expone datos médicos/PHR o PII? No por sí mismo; es una salvaguarda preventiva. Sin ella, una ruta nueva sobre datos médicos podría quedar expuesta sin que nada lo detecte.
- ¿Fuga entre escuelas? No directamente.
- Roles afectados: ninguno de forma inmediata; afecta a la seguridad de cualquier endpoint futuro.

## Propuesta de solución

1. Añadir `# PUBLIC_ROUTE` como comentario encima de cada función pública listada y moverlo fuera del docstring en `catalogs.py`.
2. Crear `tests/api/test_route_protection.py` según `vitaly-rbac` (recorre `app.routes`, busca `get_current_user_token` en el árbol de dependencias o el marcador). Una vez estable, endurecer `_is_public` para aceptar solo el comentario (`inspect.getcomments`) y no el docstring.
3. El test fallará mientras exista el gap de `academic_year` (#14); conviene fusionar primero esa corrección o marcar el caso como `xfail` con referencia al issue.

**Pregunta abierta:** ¿`/health` y `/health-visual` deben seguir siendo públicos? `/health` devuelve `str(e)` del error de base de datos (`app/main.py:63`).

## Criterios de aceptación

- [ ] Cada ruta pública listada tiene la línea `# PUBLIC_ROUTE` inmediatamente encima de su `def` (o de su decorador, según el formato que fije la regla).
- [ ] Ningún docstring contiene `# PUBLIC_ROUTE`.
- [ ] `tests/api/test_route_protection.py` existe y pasa con `pytest tests/api/test_route_protection.py`.
- [ ] El test falla si se añade una ruta de prueba sin gate ni marcador.
- [ ] La nota de legado en `.agents/rules/rbac-enforcement.md:21` y la sección "Known rule drift" de `vitaly-rbac` se actualizan.

## Referencias

- `.agents/rules/rbac-enforcement.md`
- Skill `vitaly-rbac` (sección "Guard test: no ungated route")
- #14 (`academic_year` sin autenticación)
