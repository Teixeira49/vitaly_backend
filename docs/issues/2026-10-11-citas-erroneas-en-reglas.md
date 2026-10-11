---
title: "[📝 Docs] Corregir citas a código inexistente o legado en reglas"
labels: [documentation, P3, agents]
issue: 23
url: https://github.com/Teixeira49/vitaly_backend/issues/23
---

## Descripción
Dos reglas de agentes citan código del repositorio de forma incorrecta: una usa un método de servicio que no existe y otra presenta como patrón a seguir una función que también contiene comportamiento legado prohibido por otra regla. Un agente que siga estas citas puede inventar nombres o replicar el antipatrón.

## Evidencia
- `.agents/rules/empty-table-validation.md:57` y `:75` — el ejemplo "DO" define y llama `admin_service.list_schools()`. El método real es `get_schools(self, page: int, size: int)` en `app/services/admin_service.py:397`.
- `.agents/rules/tenant-isolation.md:28` — cita `get_students_by_classroom` como patrón de pertenencia indirecta. Su verificación de pertenencia sí es correcta (`app/services/school_admin_service.py:371-377`: 404 si no existe el salón, 403 si es de otra escuela), pero la misma función responde 404 ante un salón sin estudiantes (`app/services/school_admin_service.py:389-393`), lo que viola `empty-table-validation.md` §2 (colección vacía → 200 con `data=[]`). La skill `vitaly-feature-testing` ya la lista como legado.

## Comportamiento actual vs esperado
- **Actual:** la regla de tablas vacías usa un nombre de método inexistente; la regla de aislamiento cita sin matices una función con un antipatrón.
- **Esperado:** los ejemplos se marcan como ilustrativos o usan nombres reales, y la cita de `get_students_by_classroom` se limita a su verificación de pertenencia.

## Impacto
- ¿Expone datos médicos/PHR o PII? No.
- ¿Fuga entre escuelas (school_id)? No.
- Roles afectados: ninguno en runtime; afecta a la calidad del código que generan los agentes.

## Propuesta de solución
1. `empty-table-validation.md`: marcar el ejemplo como ilustrativo o renombrarlo para que coincida con `get_schools(page, size)`.
2. `tenant-isolation.md:28`: precisar "patrón de verificación de pertenencia usado en `get_students_by_classroom` (solo la comprobación de pertenencia; su 404 ante lista vacía es legado)".

Fuera de alcance: corregir el 404 de lista vacía en `get_students_by_classroom` es un cambio de código con impacto en el frontend; si se aprueba, conviene un issue de tipo bug aparte.

## Criterios de aceptación
- [ ] Ninguna regla referencia `list_schools` como método real, o el ejemplo está marcado como ilustrativo.
- [ ] `tenant-isolation.md` cita `get_students_by_classroom` solo como patrón de pertenencia, con la nota de legado.
- [ ] `grep -n "list_schools\|get_students_by_classroom" .agents/rules/*.md` refleja ambos cambios.

## Referencias
- `.agents/rules/empty-table-validation.md`, `.agents/rules/tenant-isolation.md`.
- Skill `vitaly-feature-testing` (inventario de 404 legado).
