---
name: confiao-contracts-parity
description: Paridad entre los esquemas Zod de packages/contracts y los DTO Pydantic de apps/api en Confiao Chatbot. Úsala siempre que se cree o modifique un endpoint, un archivo presentation/schemas.py, un esquema de packages/contracts/src, un formulario del panel o un tipo compartido entre web y API — y también cuando se hable de contratos, DTO, validación, snake_case, z.infer, response_model o de que el panel y la API dejaron de entenderse. Ningún compilador cruza la frontera Python/TypeScript: si un cambio toca un lado del contrato, esta skill dice qué hacer con el otro.
---

# Paridad de contratos Zod ↔ Pydantic

`@confiao/contracts` es la fuente de verdad del contrato entre el panel y la API, pero esa verdad
está declarada dos veces: una en TypeScript con Zod y otra en Python con Pydantic. Nada verifica
que sigan coincidiendo. `tsc` valida el lado TypeScript, `mypy` valida el lado Python, y ninguno de
los dos ve al otro.

El resultado es un fallo silencioso: el panel valida un campo que la API acepta más laxo, o envía
un valor que la API rechaza, y nadie se entera hasta que un usuario lo encuentra. Esta skill existe
para que ese desajuste se detecte al escribirlo, no en producción.

## La regla

**Un cambio de contrato toca los dos lados en el mismo commit.** Si editas
`apps/api/src/<slice>/presentation/schemas.py`, abre `packages/contracts/src/<slice>.ts` antes de
dar el cambio por terminado. Y al revés.

Los campos viajan en **snake_case** en ambos lados, igual que en la API. No hay conversión a
camelCase en la frontera: es una decisión tomada, y mantenerla evita una capa de traducción que
solo serviría para introducir errores.

## Tabla de equivalencias

| Zod (TypeScript)                     | Pydantic (Python)                            | Nota                                                    |
| ------------------------------------ | -------------------------------------------- | ------------------------------------------------------- |
| `z.string()`                         | `str`                                         |                                                         |
| `z.string().min(1).max(50)`          | `str = Field(min_length=1, max_length=50)`    | Los límites deben coincidir en número                   |
| `uuidSchema`                         | `UUID`                                        | En Zod 4 es `z.uuid()`, no `z.string().uuid()`          |
| `z.string()` para fechas             | `datetime`                                    | Correcto: JSON no tiene tipo fecha, viaja ISO-8601      |
| `z.enum([...])`                      | `Literal[...]` o `StrEnum`                    | Ver el ejemplo de abajo: aquí es donde más se rompe     |
| `z.number().int().min(0)`            | `int = Field(ge=0)`                           |                                                         |
| `z.boolean()`                        | `bool`                                        |                                                         |
| `z.array(x)`                         | `list[X]`                                     |                                                         |
| `z.object({...})`                    | subclase de `ApiModel`                        |                                                         |
| `.optional()`                        | `X \| None = None`                            | El campo puede **faltar**                               |
| `.nullable()`                        | `X \| None`                                   | El campo está presente y vale `null`                    |
| `.default('')`                       | `= ""`                                        | El valor por defecto debe ser el mismo                  |
| `z.unknown()`                        | `Any`                                         |                                                         |
| `z.record(z.unknown())`              | `dict[str, Any]`                              |                                                         |

`.optional()` y `.nullable()` no son intercambiables, y confundirlos produce respuestas que fallan
la validación en un lado y pasan en el otro. Si el campo puede venir ausente, es `.optional()`; si
viene siempre pero a veces vacío, es `.nullable()`.

## Ejemplo real de desajuste

Este existe hoy en el repositorio y sirve como patrón de lo que hay que buscar:

```typescript
// packages/contracts/src/bots.ts
export const BOT_STATUSES = ['draft', 'published'] as const;
export const botStatusSchema = z.enum(BOT_STATUSES);

export const botSchema = z.object({
  status: botStatusSchema,          // solo dos valores posibles
});
```

```python
# apps/api/src/bots/presentation/schemas.py
class BotResponse(ApiModel):
    status: str                      # cualquier cadena
```

El panel garantiza que nunca enviará un estado inválido, pero la API aceptaría
`status="cualquier cosa"` de cualquier otro cliente —incluido el runtime, o una llamada con API
key— y lo guardaría. La corrección es estrechar el lado Python:

```python
BotStatus = Literal["draft", "published"]

class BotResponse(ApiModel):
    status: BotStatus
```

El mismo patrón aparece en `ContextSettings`: Zod limita `positive_prompts` y `negative_prompts` a
4000 caracteres y `general_topic` a 1000; el modelo Pydantic no impone ninguno. Quien valide primero
no importa — lo que importa es que la API nunca dependa de que el cliente haya validado.

**La asimetría siempre se corrige del lado laxo hacia el estricto.** El panel es un cliente entre
varios; la API es la última línea.

## Verificar contra el OpenAPI

La API publica su esquema en `/api/openapi.json`, generado a partir de los modelos Pydantic reales.
Eso da una forma objetiva de contrastar los dos lados sin leerlos en paralelo:

```bash
curl -s http://localhost:8000/api/openapi.json | jq '.components.schemas.BotResponse'
```

Cuando revises un contrato, compara ese bloque con el esquema Zod correspondiente y busca cuatro
cosas concretas: nombres de campo idénticos, tipos equivalentes según la tabla, límites numéricos
iguales, y el mismo conjunto de campos obligatorios. Esas cuatro cubren casi todos los desajustes
reales.

Es también la base natural de una comprobación automática en CI, que es donde este trabajo debería
acabar: el OpenAPI ya existe, así que la verificación no requiere escribir un tercer contrato.

## Zod 4

El proyecto declara `zod ^4.4.3`. Las formas de v3 siguen apareciendo en el código —
`packages/contracts/src/common.ts` todavía usa `z.string().uuid()` — pero no son el idioma a copiar.
En v4 los validadores de formato son funciones de primer nivel: `z.uuid()`, `z.email()`, `z.url()`.
Cuando toques un esquema por otro motivo, actualiza de paso las formas antiguas que encuentres en
él; migrar un archivo entero de golpe no hace falta.

## Al agregar un endpoint

1. Escribe el DTO Pydantic en `presentation/schemas.py`, heredando de `ApiModel`.
2. Escribe el esquema Zod hermano en `packages/contracts/src/<slice>.ts`, con su
   `export type X = z.infer<typeof xSchema>`.
3. Contrasta ambos con la tabla de equivalencias.
4. Si el endpoint devuelve una lista paginada, usa `Page[X]` en Python y `paginatedSchema(x)` en
   TypeScript: la envoltura ya está resuelta en `shared/schemas.py` y en `contracts/common.ts`.
5. Si el endpoint puede fallar de forma esperada, el error viaja con la forma `ApiError`
   (`code`, `message`, `detail?`, `request_id?`). No inventes formas de error nuevas.

## Señales de alarma

- Un campo `str` en Pydantic cuyo equivalente Zod es `z.enum(...)`.
- Límites `min`/`max` presentes en un lado y ausentes en el otro.
- Un DTO nuevo sin esquema Zod correspondiente, o al revés.
- camelCase en cualquiera de los dos lados.
- Un formulario del panel que valida con un esquema local en vez de con el de `@confiao/contracts`.
- Un tipo TypeScript escrito a mano en `apps/web` en lugar de derivarlo con `z.infer`.
