# [Nombre del Rol o Dominio]

> Plantilla para guías sin frontmatter: archivos de rol en `.agents/roles/` o
> secciones de `.agents/AGENTS.md`. Las reglas con alcance por archivos usan
> `rule-template.md` (frontmatter + 5 secciones) en `.agents/rules/`.

## Alcance
Define los límites operativos y los estándares de implementación para [Dominio/Módulo].

## Límites y Restricciones
- **Multi-tenancy / Seguridad:** [ej. nunca confiar en el `school_id` enviado por el cliente]
- **Patrones Prohibidos:** [ej. validaciones de rol inline, respuestas sin `APIResponse`]

## Convenciones
- **Capas:** Endpoint (`app/api/v1/endpoints/`) -> Servicio (`app/services/`) -> cliente supabase-py.
- **Respuestas:** Envelope `APIResponse[T]` obligatorio.
- **Documentación:** Docstrings estilo Google con `Args`, `Returns` y `Raises`.

## Ejemplos
### ❌ Prohibido
```python
# Implementación insegura o fuera de estándar
```

### ✅ Aprobado
```python
# Implementación conforme al estándar
```

## Verificación
- Comandos de validación o suites de tests a ejecutar antes de cerrar el cambio.
