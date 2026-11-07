---
description: "Protocolo obligatorio de autorización previa y análisis de impacto para migraciones de base de datos"
globs:
  - "supabase/migrations/**/*.sql"
alwaysApply: false
---

# Protocolo de Migración y Cambios en Base de Datos

## 1. Scope & Context
- **Target Area:** Migraciones SQL de Supabase (`supabase/migrations/`) y ejecución de sentencias DDL/DML sobre PostgreSQL/Supabase (MCP `apply_migration` / `execute_sql`, CLI `supabase db push`).
- **Roles:** Database Specialist.
- **Objetivo:** Proteger la integridad de los datos en PostgreSQL/Supabase, requiriendo validación humana explícita antes de cualquier alteración de esquema o mutación masiva.

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** ejecutes comandos como `apply_migration`, `execute_sql` (con DDL/DML), `supabase db push` o sentencias DDL destructivas (`DROP`, `ALTER`, `TRUNCATE`) sin recibir confirmación explícita del **USUARIO**.
- ⛔ **NUNCA** apliques migraciones que eliminen columnas en producción sin una fase previa de desuso o backup.
- 🔒 **MANDATORIO:** Las operaciones de solo lectura (`SELECT`) están permitidas sin autorización previa, siempre que no expongan credenciales o datos sensibles innecesariamente.
- 🔒 **MANDATORIO:** Todo cambio de esquema se versiona como archivo SQL en `supabase/migrations/` con el formato de nombre `YYYYMMDDHHMMSS_descripcion.sql`.

## 3. Directivas Prescriptivas
Antes de proceder con cualquier modificación de esquema, el agente debe presentar un informe estructurado que contenga:
1. **Objetivo del Cambio:** Explicación técnica de la necesidad.
2. **Tablas Afectadas:** Listado exhaustivo de tablas, llaves foráneas e índices.
3. **Análisis de Impacto:**
   - Nuevas columnas o tablas agregadas (las tablas con alcance de escuela deben incluir `school_id` e índice, ver `tenant-isolation.md`).
   - Modificación de tipos de datos o constraints (`NOT NULL`, `UNIQUE`).
   - Impacto en código existente: esquemas Pydantic (`app/schemas/`), consultas `supabase.table(...)` en servicios (`app/services/`) y endpoints, y contratos con el frontend (ver `cross-repo-e2e.md`).
   - Riesgo de pérdida o corrupción de datos.
4. **Sentencia SQL / Código de Migración Exacto:** Mostrar el código a ejecutar.
5. **Pregunta Directa de Confirmación:** Solicitar autorización al usuario antes de proceder.

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
```bash
# Mal: Ejecutar la migración directamente sin consulta previa
$ supabase db push
"Migración ejecutada con éxito" # ❌ Vulneración de la regla de oro
```

### ✅ Patrón Estándar (DO)
> [!IMPORTANT]
> **Propuesta de Migración de Base de Datos**
>
> **Objetivo:** Añadir soporte para historiales por año académico en las métricas de salud.
> **Tablas Afectadas:** `public.student_metrics`, `public.academic_year`
> **Análisis de Impacto:**
> - Columna `academic_year_id` (bigint) añadida como nullable (sin impacto en registros previos).
> - Llave foránea hacia `public.academic_year(id)`.
> - Código afectado: esquemas Pydantic de métricas en `app/schemas/` y las consultas de métricas en `app/services/school_admin_service.py`.
>
> **Archivo propuesto:** `supabase/migrations/20261011000000_add_academic_year_to_student_metrics.sql`
> ```sql
> ALTER TABLE public.student_metrics
> ADD COLUMN IF NOT EXISTS academic_year_id bigint REFERENCES public.academic_year(id);
> ```
> **¿Deseas que ejecute esta migración ahora?**

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] El informe de migración fue presentado al usuario.
  - [ ] El usuario otorgó confirmación afirmativa explícita.
  - [ ] El SQL es idempotente (`IF NOT EXISTS` / `IF EXISTS`) o está encapsulado en una transacción segura.
  - [ ] Los esquemas Pydantic y servicios afectados fueron actualizados.
- **Comando de Verificación:** `supabase db lint` (requiere Supabase CLI vinculado al proyecto). Si el CLI no está disponible, no lo instales ni lo configures por tu cuenta: informa al usuario y deja que decida cómo validar la migración (revisión manual del SQL o ejecución en su entorno).
