---
description: "Validación de existencia previa de registros y manejo de tablas vacías en SQLAlchemy"
globs:
  - "app/services/**/*.py"
  - "app/api/**/*.py"
alwaysApply: false
---

# Validación de Existencia y Tablas Vacías

## 1. Scope & Context
- **Target Area:** Servicios (`app/services/`) y endpoints (`app/api/`) que interactúan con la base de datos PostgreSQL mediante SQLAlchemy.
- **Roles:** Database Specialist, Backend Architect.
- **Objetivo:** Prevenir errores 500 silenciosos y fallos en cascada al operar sobre registros o tablas sin datos previos, respetando la semántica de la API REST.

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** devuelvas `HTTPException(404)` al consultar colecciones o listas vacías (`GET /users`). Las colecciones vacías deben responder con `200 OK` y `data=[]`.
- ⛔ **NUNCA** ejecutes mutaciones (`UPDATE`, `DELETE`) asumiendo que el registro existe sin validar previamente o capturar la ausencia del registro.
- ⛔ **NUNCA** uses el cliente REST de Supabase (`supabase.table(...)`) dentro del backend; utiliza la sesión de SQLAlchemy (`db: Session`).

## 3. Directivas Prescriptivas

1. **Listados y Colecciones:**
   - Si una consulta retorna una lista vacía, devuelve `APIResponse(success=True, data=[], message="No se encontraron registros")`.
2. **Operaciones sobre Recurso Individual (`GET /item/{id}`, `PUT`, `DELETE`):**
   - Comprueba la existencia del registro por su ID y `escuela_id`.
   - Si no existe, lanza de inmediato `HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")`.
3. **Tablas Catálogo / Prerrequisitos de Negocio:**
   - Si una operación requiere que existan datos base configurados (ej. `CicloLectivo`, `CatalogoVacunas`), realiza una verificación ligera con `exists()` o `first()` antes de procesar transacciones complejas.

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
```python
# Mal: Retorna 404 al listar una colección vacía, o usa cliente no estándar
@router.get("/schools", response_model=APIResponse[list[SchoolRead]])
def list_schools(db: Session = Depends(get_db)):
    schools = db.query(School).all()
    if not schools:
        # ❌ ERROR: Rompe el estándar REST (debería ser 200 con lista vacía)
        raise HTTPException(status_code=404, detail="No hay escuelas registradas")
    return APIResponse(success=True, data=schools, message="Escuelas obtenidas")
```

### ✅ Patrón Estándar (DO)
```python
# Bien: Colección retorna 200 con data=[], y mutación verifica existencia antes de actuar
@router.get("/schools", response_model=APIResponse[list[SchoolRead]], summary="Listar escuelas")
def list_schools(db: Session = Depends(get_db)) -> APIResponse[list[SchoolRead]]:
    schools = school_service.get_all(db)
    message = "Escuelas recuperadas exitosamente" if schools else "No hay escuelas registradas actualmente"
    return APIResponse(success=True, data=schools, message=message)

@router.put("/schools/{school_id}", response_model=APIResponse[SchoolRead], summary="Actualizar escuela")
def update_school(
    school_id: int,
    payload: SchoolUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([RoleEnum.ADMIN_SISTEMA]))
) -> APIResponse[SchoolRead]:
    school = school_service.get_by_id(db, school_id=school_id)
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La escuela con ID {school_id} no existe"
        )
    updated = school_service.update(db, db_obj=school, obj_in=payload)
    return APIResponse(success=True, data=updated, message="Escuela actualizada exitosamente")
```

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] Colecciones (`GET /recursos`) retornan código 200 y array vacío cuando no hay registros.
  - [ ] Recursos individuales (`GET/PUT/DELETE /recursos/{id}`) lanzan 404 si el recurso no existe.
  - [ ] Uso exclusivo de `db: Session` (SQLAlchemy).
- **Comando de Verificación:** `pytest tests/services/ tests/api/ -k "not_found or empty"`
