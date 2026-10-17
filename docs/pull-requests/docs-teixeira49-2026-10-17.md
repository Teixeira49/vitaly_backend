# [📝 Doc] - Documentar recomendaciones de CI/CD

## Descripción

Documenta en `docs/research/ci_cd_recomendaciones.md` las mejoras propuestas para ampliar la integración continua y añadir despliegues por ambientes al backend.

- Prioriza protección de ramas, auditoría de dependencias, Dependabot, cobertura, instalaciones reproducibles, validación OpenAPI y despliegue con verificación posterior.
- Incluye fuentes oficiales, esfuerzos estimados y un flujo de staging y producción.
- Explica que `/health` devuelve HTTP 200 aunque falle Supabase y que el smoke test debe comprobar el campo `database`.
- Distingue el CI revisado en `ci/GH-35` de la base `development`, que aún no contiene ese workflow.

Cambio exclusivamente documental; no agrega dependencias ni variables de entorno. Sin issue asociado. Base: `development`.

## Tipo de cambio

- [ ] ✨ Nueva funcionalidad (cambio no-breaking que agrega funcionalidad)
- [ ] 🛠️ Corrección de errores (cambio no-breaking que arregla un error)
- [ ] ❌ Cambio importante (arreglo o característica que haría que la funcionalidad existente no funcionara como se esperaba)
- [x] 📝 Actualización de la documentación
- [ ] 🧹 Code refactoring (modificación de la estructura interna del código sin modificar las APIs)
- [ ] ✅ Build configuration change (modificación de los archivos para hacer deploy)
- [ ] 🗑️ Chore (actividades que no modifican la interacción con la app, por ejemplo, modificar la configuración del linter)

## ¿Cómo se ha probado esto?

- [x] Revisión del diagnóstico contra la rama de CI y la base `development`.
- [x] Suite existente: 272 pruebas pasan con credenciales ficticias y conexiones de red bloqueadas.
- [x] Revisión del Markdown y comprobación de whitespace mediante `git diff --cached --check`.

**Configuración de prueba:**

- Python 3.10 y entorno de desarrollo existente con `pytest-socket`.
- Variables ficticias: `SUPABASE_URL=http://127.0.0.1:54321`, `SUPABASE_KEY=test-supabase-key` y `SECRET_KEY=test-secret-key-not-for-production`.
- Comando: `python -m pytest -q -p no:cacheprovider --disable-socket --allow-unix-socket`.
- No requiere servidor ni pruebas manuales de endpoints; no se modifican APIs.
- Se observan 38 advertencias de deprecación existentes de Pydantic y respuestas 422.

## Lista de Verificación

- [ ] He agregado las nuevas dependencias en la descripción (no aplica)
- [ ] He agregado las nuevas variables de entorno (solo los nombres y rutas) a la descripción (no aplica)
- [x] Mi código sigue las pautas de estilo de este proyecto
- [x] He realizado una auto-revisión de mi código
- [ ] He comentado mi código, particularmente en áreas difíciles de entender (no aplica; solo documentación)
- [x] He realizado los cambios correspondientes a la documentación.
- [x] Mis cambios no generan nuevas advertencias
- [ ] Mis cambios pasan el build y lint del proyecto localmente (no aplica; solo Markdown)
- [ ] He agregado pruebas que prueban que mi solución es efectiva o que mi función funciona (no aplica)
- [x] Las pruebas unitarias nuevas y existentes pasan localmente con mis cambios
