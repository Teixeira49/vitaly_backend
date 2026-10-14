# [✅ Build: GH-35] - Validar pull requests con Ruff y pytest

## Descripción

Añade GitHub Actions para detectar errores críticos de Python y regresiones en
los pull requests antes de integrarlos. El workflow también se ejecuta en pushes
a `development` y `main`, y permite ejecución manual.

- Ejecuta Ruff y pytest con Python 3.10 y caché de pip.
- Aísla la configuración de pruebas del `.env` local con credenciales ficticias.
- Bloquea conexiones de red con pytest-socket; permite sockets Unix para TestClient.
- Limita permisos a lectura, fija un timeout y cancela ejecuciones obsoletas.
- Documenta los comandos locales y la configuración del check obligatorio.

Nueva dependencia de desarrollo: `pytest-socket>=0.7.0,<1`. Se conserva
`ruff>=0.17.0,<0.18.0`, ya presente en `development`.
No requiere nuevas variables de entorno ni secretos de GitHub.

Base: `development`. Rama: `ci/GH-35`.

Closes #35

## Tipo de cambio

- [ ] ✨ Nueva funcionalidad (cambio no-breaking que agrega funcionalidad)
- [ ] 🛠️ Corrección de errores (cambio no-breaking que arregla un error)
- [ ] ❌ Cambio importante (arreglo o característica que haría que la funcionalidad existente no funcionara como se esperaba)
- [x] 📝 Actualización de la documentación
- [ ] 🧹 Code refactoring (modificación de la estructura interna del código sin modificar las APIs)
- [x] ✅ Build configuration change (modificación de los archivos para hacer deploy)
- [x] 🗑️ Chore (actividades que no modifican la interacción con la app, por ejemplo, modificar la configuración del linter)

## ¿Cómo se ha probado esto?

- [x] `python -m pip install -r requirements-dev.txt`: dependencias instaladas.
- [x] `python -m ruff check app tests`: sin errores.
- [x] `python -m pytest -q`: 272 pruebas pasan con conexiones de red bloqueadas.
- [x] `git diff HEAD --check`: sin errores de whitespace.
- [ ] Abrir o actualizar un PR: comprobar que aparece **Lint and tests** y pasa.
- [ ] Introducir temporalmente un fallo de lint o pytest en una rama de prueba:
  comprobar que el check falla y luego revertir ese cambio.
- [ ] Tras la primera ejecución, configurar el check obligatorio en las ramas protegidas.

**Configuración de prueba:**

- Python 3.10 y dependencias de `requirements-dev.txt`.
- Pruebas automatizadas: `python -m pytest -q`.
- No requiere servidor, Swagger ni credenciales de servicios externos.
- Se observan 38 advertencias de deprecación en código existente de Pydantic y
  respuestas 422; no bloquean la suite.

## Lista de Verificación

- [x] He agregado las nuevas dependencias en la descripción
- [ ] He agregado las nuevas variables de entorno (solo los nombres y rutas) a la descripción (no aplica)
- [x] Mi código sigue las pautas de estilo de este proyecto
- [x] He realizado una auto-revisión de mi código
- [x] He comentado mi código, particularmente en áreas difíciles de entender
- [x] He realizado los cambios correspondientes a la documentación.
- [x] Mis cambios no generan nuevas advertencias
- [x] Mis cambios pasan el build y lint del proyecto localmente
- [ ] He agregado pruebas que prueban que mi solución es efectiva o que mi función funciona (se utiliza la suite existente)
- [x] Las pruebas unitarias nuevas y existentes pasan localmente con mis cambios
