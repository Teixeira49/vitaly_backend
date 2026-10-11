---
name: export-patterns
description: >
  Patrones para exportaciones CSV/Excel y descargas de archivos: sanitización
  contra CSV injection, headers HTTP correctos y streaming. Usar cuando se
  agregue o modifique un endpoint de exportación o descarga de datos.
metadata:
  owner: estei-empresas
  format: agent-skills-v1
---

# Export Patterns — Exportaciones CSV y Excel

## Seguridad: CSV injection

CSV injection ocurre cuando un valor empieza con `=`, `+`, `-`, `@`, `\t` o `\r\n` — Excel los interpreta como fórmulas y puede ejecutar código malicioso en la máquina del usuario.

**Función canónica** — `ExportController.sanitizeForCSV(value)`:

1. Convierte a string, devuelve `''` si es `null`/`undefined`.
2. Si empieza con carácter peligroso → prefija con `'` (apóstrofe).
3. Si contiene `,`, `"` o saltos de línea → envuelve en comillas dobles y escapa `"` → `""`.

**Regla**: todo valor que va a un CSV pasa por `sanitizeForCSV`. Sin excepciones. Incluir headers.

## Headers HTTP obligatorios

### CSV

```ts
res.setHeader('Content-Type', 'text/csv; charset=utf-8');
res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
res.setHeader('Pragma', 'no-cache');
res.setHeader('Expires', '0');
```

### Excel (.xlsx)

```ts
res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
```

**Por qué Cache-Control**: el navegador no debe cachear exportaciones — los datos cambian y pueden contener información sensible.

## Patrón CSV

```ts
// 1. Generar nombre de archivo con fecha
const filename = `entidades_${new Date().toISOString().split('T')[0]}.csv`;

// 2. Definir headers y filas (arrays de primitivos)
const headers = ['ID', 'Nombre', 'Estado'];
const rows = data.map((item) => [item.id, item.name, item.status]);

// 3. Generar contenido — usar generateCSV() del ExportController
const csvContent = this.generateCSV(headers, rows);

// 4. Audit log ANTES de enviar
await this.auditService.logDataExport(
  this.auditService.extractContextFromRequest(req),
  'nombre_export_type', // snake_case, descriptivo
  rows.length,
  { filtros, aplicados }
);

// 5. Headers + send
res.setHeader('Content-Type', 'text/csv; charset=utf-8');
res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
res.setHeader('Pragma', 'no-cache');
res.setHeader('Expires', '0');
res.status(200).send(csvContent);
```

## Patrón Excel

```ts
// 1. Crear workbook y worksheet
const workbook = new ExcelJS.Workbook();
const worksheet = workbook.addWorksheet('Nombre Hoja');

// 2. Definir columnas con width
worksheet.columns = [
  { header: 'Columna', key: 'key', width: 20 },
];

// 3. Estilizar header row (obligatorio — legibilidad)
const headerRow = worksheet.getRow(1);
headerRow.font = { bold: true };
headerRow.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE0E0E0' } };
headerRow.alignment = { vertical: 'middle', horizontal: 'left' };

// 4. Agregar filas + formatear celdas numéricas
data.forEach(item => {
  const row = worksheet.addRow({ key: item.value });
  row.getCell('montoUSD').numFmt = '"$"#,##0.00';
});

// 5. Serializar a Buffer
const buffer = await workbook.xlsx.writeBuffer();
const filename = `reporte_${format(new Date(), 'yyyyMMdd_HHmmss')}.xlsx`;

// 6. Audit log ANTES de enviar
await this.auditService.logDataExport(..., rows.length, filters);

// 7. Headers + send buffer
res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
res.send(buffer);
```

**Lógica compleja**: encapsularla en un `*ExportService` en `application/services/` (ver `FinancialExportService`, `DepartmentExportService`). El controller solo hace wiring HTTP y audit.

## Audit logging

Usar `AuditLogService.logDataExport()` en **todos** los endpoints de exportación:

```ts
await this.auditService.logDataExport(
  this.auditService.extractContextFromRequest(req), // contexto: userId, IP, userAgent
  'reservation_data', // tipo de export — snake_case
  reservationData.length, // cantidad de registros exportados
  { role, clientId, dateFrom, dateTo } // filtros aplicados (puede ser undefined)
);
```

Esto registra: `DATA_EXPORTED` sobre `REPORT`, con `exportType`, `recordCount`, `filters`, `exportedAt`.

**Cuándo**: siempre después de generar el contenido y antes de enviar la respuesta. Si la generación falla, loggear el error con `logAction` marcando `success: false`.

## Anti-patrones

- **Sin sanitización CSV**: no procesar valores directamente. Un nombre de empresa `=CMD|'/C calc'!A0` puede ejecutar una calculadora en la máquina del usuario.
- **Cachear respuestas de export**: nunca poner `Cache-Control: public` ni omitir el header — los CDNs o el browser pueden servir datos stale o de otro usuario.
- **No loggear**: toda exportación es trazabilidad financiera/operativa. Sin log no hay auditoría.
- **Generar en memoria para datasets grandes**: usar streams o paginación en la query si el dataset puede superar ~50k filas. `workbook.xlsx.writeBuffer()` carga todo en RAM.
- **Instanciar repos en el controller**: el `ExportController` instancia repositorios en métodos individuales vía `import()` dinámico para el Excel financiero — aceptable por legado, pero lo correcto es inyectarlos en el constructor.

## Referencia canónica

`ExportController.exportReservationData()` — hace todo bien:

- Sanitiza con `generateCSV()` → `sanitizeForCSV()`
- Llama `logDataExport()` con tipo, count y filtros de contexto
- Setea los 5 headers (incluye `Pragma` y `Expires`)
- Maneja errores con `logAction` + `success: false`

## Checklist

Antes de agregar un endpoint de exportación:

- [ ] ¿Los valores CSV pasan por `sanitizeForCSV`? (vía `generateCSV`)
- [ ] ¿Se setean los 3 headers mínimos? (`Content-Type`, `Content-Disposition`, `Cache-Control`)
- [ ] ¿Se llama `logDataExport` con tipo, count y filtros?
- [ ] ¿El nombre de archivo incluye timestamp o fecha?
- [ ] ¿Los errores se loggean con `logAction` + `success: false`?
- [ ] ¿La lógica compleja está en un `*ExportService`, no en el controller?
- [ ] ¿El endpoint está registrado en `shared/access-control/`?
