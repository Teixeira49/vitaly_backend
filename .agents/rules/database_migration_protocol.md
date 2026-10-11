---
description: "Protocolo obligatorio de autorización previa y análisis de impacto para migraciones de base de datos"
globs:
  - "supabase/migrations/**/*.sql"
  - "alembic/**/*.py"
alwaysApply: false
---

# Protocolo de Migración y Cambios en Base de Datos

## 1. Scope & Context
- **Target Area:** Migraciones de base de datos (`supabase/migrations/`, `alembic/`) y ejecución de sentencias DDL/DML.
- **Roles:** Database Specialist.
- **Objetivo:** Proteger la integridad de los datos en PostgreSQL/Supabase, requiriendo validación humana explícita antes de cualquier alteración de esquema o mutación masiva.

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** ejecutes comandos como `apply_migration`, `execute_sql`, `alembic upgrade` o sentencias DDL destructivas (`DROP`, `ALTER`, `TRUNCATE`) sin recibir confirmación explícita del **USUARIO**.
- ⛔ **NUNCA** apliques migraciones que eliminen columnas en producción sin una fase previa de desuso o backup.
- 🔒 **MANDATORIO:** Las operaciones de solo lectura (`SELECT`) están permitidas sin autorización previa, siempre que no expongan credenciales o datos sensibles innecesariamente.

## 3. Directivas Prescriptivas
Antes de proceder con cualquier modificación de esquema, el agente debe presentar un informe estructurado que contenga:
1. **Objetivo del Cambio:** Explicación técnica de la necesidad.
2. **Tablas Afectadas:** Listado exhaustivo de tablas, llaves foráneas e índices.
3. **Análisis de Impacto:**
   - Nuevas columnas o tablas agregadas.
   - Modificación de tipos de datos o constraints (`NOT NULL`, `UNIQUE`).
   - Impacto en código existente (modelos SQLAlchemy, servicios, esquemas).
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
> - Modelos SQLAlchemy afectados: `StudentMetric`.
>
> **SQL Propuesto:**
> ```sql
> ALTER TABLE public.student_metrics 
> ADD COLUMN academic_year_id bigint REFERENCES public.academic_year(id);
> ```
> **¿Deseas que ejecute esta migración ahora?**

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] El informe de migración fue presentado al usuario.
  - [ ] El usuario otorgó confirmación afirmativa explícita.
  - [ ] El SQL es idempotente o está encapsulado en una transacción segura.
- **Comando de Verificación:** `supabase db lint` o `alembic check`
