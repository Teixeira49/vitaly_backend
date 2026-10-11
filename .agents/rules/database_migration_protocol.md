# Protocolo de Migración y Cambios en Base de Datos

Este documento define la regla obligatoria para cualquier interacción del agente de IA con la base de Datos de Supabase/PostgreSQL.

## Regla de Oro
**NUNCA** ejecutes un comando `apply_migration`, `execute_sql` o cualquier operación que altere el esquema o los datos de la base de datos sin recibir una confirmación explícita del **USUARIO**.

## Pasos Obligatorios antes de Aplicar Cambios

Antes de proceder con cualquier modificación, el agente debe presentar un informe detallado que incluya:

1.  **Objetivo del Cambio:** Explicación técnica de por qué se necesita la modificación.
2.  **Tablas Afectadas:** Listado de todas las tablas y relaciones que sufrirán cambios.
3.  **Análisis de Impacto:** 
    *   Nuevas columnas o tablas.
    *   Cambios en tipos de datos.
    *   Posible impacto en el código existente (servicios, endpoints).
    *   Impacto en los datos actuales (si hay riesgo de pérdida o corrupción).
4.  **Sentencia SQL Exacta:** Mostrar el código SQL que se pretende ejecutar.
5.  **Solicitud de Permiso:** Una pregunta directa solicitando autorización para ejecutar.

## Ejemplo de Respuesta Esperada
> [!IMPORTANT]
> **Propuesta de Migración de Base de Datos**
>
> **Objetivo:** Añadir soporte para historiales por año académico en las métricas de salud.
> **Cambios:** 
> - Tabla `public.student_metrics`: Agregar columna `academic_year_id` (bigint).
> - Referencia: `public.academic_year(id)`.
> **Impacto:** Permite filtrar métricas por año. No afecta datos existentes (columna opcional inicial).
> 
> **SQL:**
> ```sql
> ALTER TABLE public.student_metrics ADD COLUMN academic_year_id bigint REFERENCES public.academic_year(id);
> ```
> **¿Deseas que ejecute esta migración ahora?**

## Excepciones
Cualquier comando de solo lectura (`SELECT`) está permitido sin autorización previa, siempre que no exponga datos sensibles de forma innecesaria.
