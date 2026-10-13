---
description: "Aislamiento estricto multi-tenancy por school_id en endpoints y consultas supabase-py"
globs:
  - "app/api/**/*.py"
  - "app/services/**/*.py"
alwaysApply: false
---

# Aislamiento de Datos por Escuela (Multi-Tenancy)

## 1. Scope & Context
- **Target Area:** Endpoints (`app/api/`), Servicios (`app/services/`) y consultas con el cliente supabase-py (`app/core/database.py`).
- **Roles:** Security Sentinel, Database Specialist, Backend Architect.
- **Objetivo:** Prevenir fugas de información entre instituciones educativas garantizando el aislamiento estricto de datos en cada operación.
- **Modelo de datos:** La columna de tenant es `school_id` (la tabla `school` tiene como PK `sch_id`).
- **Guía práctica:** El cómo (resolución por rol, consultas indirectas, estado de RLS y verificación) vive en la skill `vitaly-tenant-isolation`.

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** confíes en el `school_id` enviado en el cuerpo (`body`), headers, `path` o `query params` por el cliente para usuarios con rol de escuela (`ADMIN_ESCUELA`, `DOCTOR`, `REPRESENTANTE`).
- ⛔ **NUNCA** realices validaciones de rol en línea dentro del handler (ej. `if payload["role"] == "admin_escuela":`); la autorización pertenece a los gates `Depends(get_current_*)` de `app/api/deps.py`.
- 🔒 **MANDATORIO:** El `school_id` debe resolverse exclusivamente en el servidor a partir del usuario autenticado. El JWT **no** contiene un claim de escuela: se parte de `sub` (id de usuario) y se busca el vínculo en base de datos (para `admin_escuela`: tabla `school_administrator`, vía `SchoolAdminService._get_school_id_for_admin`).
- 🔒 **MANDATORIO:** Toda consulta de lectura, actualización o borrado sobre tablas con alcance de escuela debe incluir `.eq("school_id", school_id)` o una verificación explícita de pertenencia (excepto para `ADMIN_SISTEMA` cuando audite el sistema global).

## 3. Directivas Prescriptivas
1. **Inyección en Rutas:** Protege la ruta con el gate de rol correspondiente (ej. `Depends(get_current_admin_escuela)`) y extrae el id del usuario con `int(admin_payload["sub"])`.
2. **Delegación a Servicios:** Pasa el `user_id` al método del servicio; el servicio resuelve el `school_id` (ej. `school_id = self._get_school_id_for_admin(user_id)`, que lanza 403 si el usuario no está vinculado a ninguna escuela). Reutiliza ese helper en lugar de repetir la consulta.
3. **Filtrado en Servicios:** Encadena siempre `.eq("school_id", school_id)` en las consultas `supabase.table(...)` sobre tablas con alcance de escuela.
4. **Pertenencia Indirecta:** Si el registro llega a la escuela de forma indirecta (ej. estudiante → `classroom_registration` → `classroom`), obtén el registro padre y compara su `school_id` con el resuelto antes de continuar (patrón usado en `get_students_by_classroom` y `get_student_detail`).
5. **Registro de otra escuela → 403 (estándar):** Al operar sobre un recurso individual (`GET/PUT/PATCH/DELETE /recurso/{id}`), sigue este orden:
   1. Busca el registro solo por su id. Si `response.data` está vacío → `HTTPException(status_code=404, detail="... no existe")` (el registro realmente no existe).
   2. Si existe pero su `school_id` (directo o del registro padre) es distinto del resuelto → `HTTPException(status_code=403, detail="No tienes permiso para acceder a este recurso: pertenece a otra escuela.")`.
   3. Solo entonces lee o muta, manteniendo `.eq("school_id", school_id)` en la mutación como defensa adicional.
   No uses 404 para ocultar registros de otra escuela: el estándar del proyecto es 403 en todos los módulos.
6. **Escrituras:** Asigna `school_id` desde el valor resuelto en el servidor, nunca desde el payload.
7. **Otros roles:** Para `doctor` el alcance se resuelve a través de `doctor_to_school`; para `representante`, a través de `parent` (`user_id`) y sus estudiantes vinculados. Ver la skill `vitaly-rbac` (ownership checks).
8. **Excepción `ADMIN_SISTEMA`:** Los endpoints de auditoría global (ej. `/admin/schools/{school_id}`) pueden recibir `school_id` por path, siempre detrás de `Depends(get_current_admin_sistema)`.

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
```python
# Mal: Acepta school_id del cliente o hace validaciones de roles manuales en el cuerpo
@router.get("/classrooms")
def list_classrooms(
    school_id: int = Query(...),  # El cliente podría enviar ?school_id=999 ajeno ❌
    payload: dict = Depends(get_current_user_token),
):
    # ❌ Antipatrón de autorización inline
    if payload.get("role") != "admin_escuela":
        raise HTTPException(status_code=403, detail="No autorizado")

    rows = supabase.table("classroom").select("*").eq("school_id", school_id).execute()
    return rows.data  # ❌ Además, sin envelope APIResponse
```

### ✅ Patrón Estándar (DO)
```python
# Endpoint (ilustrativo): RBAC declarado en dependencias; el cliente no participa en la elección del tenant
@router.get("/classrooms", response_model=APIResponse[list[ClassroomRead]])
def list_classrooms(
    admin_payload: dict = Depends(get_current_admin_escuela),
):
    user_id = int(admin_payload["sub"])
    result = school_admin_service.list_classrooms(user_id=user_id)
    return APIResponse(data=result, message="Salones obtenidos exitosamente")

# Servicio: school_id resuelto en el servidor y aplicado como filtro ✅
def list_classrooms(self, user_id: int) -> list[dict]:
    school_id = self._get_school_id_for_admin(user_id)
    response = (
        supabase.table("classroom")
        .select("id, category, level, section, academic_year_id")
        .eq("school_id", school_id)
        .eq("is_deleted", False)
        .execute()
    )
    return response.data

# Servicio: recurso individual — 404 si no existe, 403 si es de otra escuela ✅
def get_classroom(self, user_id: int, classroom_id: int) -> dict:
    school_id = self._get_school_id_for_admin(user_id)
    response = (
        supabase.table("classroom")
        .select("id, school_id, category, level, section")
        .eq("id", classroom_id)
        .eq("is_deleted", False)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail=f"No existe ningún salón con ID {classroom_id}.")
    classroom = response.data[0]
    if classroom["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para acceder a este salón: pertenece a otra escuela.",
        )
    return classroom
```

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] No se lee `school_id` del payload, query o path para autorizar (salvo rutas de `ADMIN_SISTEMA`).
  - [ ] El endpoint cuenta con un gate `Depends(get_current_*)`.
  - [ ] Los métodos de servicio resuelven `school_id` desde el `user_id` y filtran con `.eq("school_id", school_id)` o verifican pertenencia.
  - [ ] Un registro existente de otra escuela responde `403`; un registro inexistente responde `404`.
  - [ ] Los catálogos globales (`states`, `school_type`, `classroom_category`, `system_status`, `academic_year`) no requieren filtro de escuela.
- **Comando de Verificación:** `pytest tests/` (los mocks solo prueban que el filtro se invoca; el aislamiento real requiere una prueba contra una instancia de Supabase con dos escuelas, ver skill `vitaly-tenant-isolation`).
