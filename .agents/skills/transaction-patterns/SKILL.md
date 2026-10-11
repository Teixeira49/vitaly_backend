---
name: transaction-patterns
description: >
  Define cuándo y cómo usar db.transaction() para operaciones atómicas
  multi-tabla, separando puerto en application/ports e implementación en
  infrastructure. Usar cuando una operación escriba en 2+ tablas o requiera
  rollback unificado.
metadata:
  owner: estei-empresas
  format: agent-skills-v1
---

# Transaction Patterns — Transacciones de Base de Datos

## Cuándo usar transacción

Una transacción es **obligatoria** cuando la operación debe ser atómica: si una parte falla, todo debe revertirse.

Usar `db.transaction()` cuando:

- Se escribe en **2 o más tablas** en la misma operación
- La integridad requiere que ambas escrituras existan o ninguna (ej: booking + travelers)
- Una operación financiera actualiza múltiples registros relacionados (pago + allocation + invoice)
- Se actualiza un estado + se inserta un registro de auditoría o historial como parte del mismo flujo
- La lógica de negocio impone una regla del tipo "si A falla, B no debe quedar guardado"

## Cuándo NO usar transacción

- Lecturas (SELECT): nunca necesitan transacción
- Un único INSERT o UPDATE atómico por naturaleza
- Operaciones idempotentes sin efectos secundarios acoplados
- Cuando el rollback manual (compensación) ya está implementado y es preferible por UX

## Patrón de implementación

Este proyecto separa la transacción en dos capas:

### 1. Interfaz en `application/ports/`

Define el contrato de la operación atómica. La capa de aplicación depende solo de esta interfaz.

```ts
// server/src/application/ports/IMyOperationTransaction.ts
export interface IMyOperationTransaction {
  execute(params: {
    entityId: string;
    // ... parámetros necesarios
  }): Promise<MyOperationResult>;
}
```

### 2. Implementación en `infrastructure/persistence/postgres/transactions/`

Usa `db.transaction(async (tx) => { ... })` directamente con Drizzle.

```ts
// server/src/infrastructure/persistence/postgres/transactions/MyOperationTransaction.ts
import { db } from '../../../../../../db';
import type { IMyOperationTransaction } from '../../../../application/ports/IMyOperationTransaction';

export class MyOperationTransaction implements IMyOperationTransaction {
  async execute(params: { entityId: string }): Promise<MyOperationResult> {
    await db.transaction(async (tx) => {
      await tx.insert(tableA).values({ ... });
      await tx.update(tableB).set({ ... }).where(eq(tableB.id, params.entityId));
    });
    return { success: true };
  }
}
```

### 3. Inyección en el command

El command recibe la interfaz por constructor y la invoca al final, después de toda la lógica de negocio.

```ts
constructor(
  private readonly repo: IMyRepo,
  private readonly myTransaction: IMyOperationTransaction
) {}

async execute(input: MyInput): Promise<MyResult> {
  // ── Pre-transaction: lecturas, validaciones, lógica de negocio ──
  const entity = await this.repo.findById(input.id);
  if (!entity) throw new EntityNotFoundError(input.id);

  // ── Atomic write ─────────────────────────────────────────────────
  await this.myTransaction.execute({ entityId: input.id });

  return { id: input.id };
}
```

**Regla**: toda la lógica de negocio y validaciones van **antes** de invocar la transacción. La transacción solo ejecuta las escrituras.

## Dónde ubicarlo

| Artefacto              | Path                                                                               |
| ---------------------- | ---------------------------------------------------------------------------------- |
| Interfaz del puerto    | `server/src/application/ports/I{Name}Transaction.ts`                               |
| Implementación Drizzle | `server/src/infrastructure/persistence/postgres/transactions/{Name}Transaction.ts` |

Naming: `{OperaciónEnPascalCase}Transaction` → ej: `BookingCancellationTransaction`, `PaymentVerificationTransaction`

## Alternativa: transacción dentro de repositorio

Cuando la operación es autónoma de un repositorio (no necesita un command propio), puede vivir como método del repositorio:

```ts
async writeCancellationAtomically(writes: CancellationWrites): Promise<void> {
  await db.transaction(async (tx) => {
    // múltiples writes...
  });
}
```

Usar este patrón solo cuando la operación no requiere lógica de negocio externa antes de la transacción.

## TransactionContext — tipo exportado

Para pasar `tx` como parámetro opcional (patrón de propagación de contexto):

```ts
import { TransactionContext } from '@db';
// Tipo: Parameters<Parameters<typeof db.transaction>[0]>[0]
```

Usar cuando un repositorio debe participar en una transacción iniciada externamente.

## Rollback y error handling

- Drizzle hace rollback automático si el callback de `db.transaction()` lanza una excepción.
- No hace falta llamar `tx.rollback()` manualmente: lanzar (`throw`) dentro del callback es suficiente.
- Los errores del `db.transaction()` se propagan normalmente; el command los deja subir sin capturar.
- No envolver `db.transaction()` en try/catch salvo para logging o transformación de error.

## Testing de transacciones

**El command se testea sin base de datos real.**

La interfaz `IMyOperationTransaction` se mockea como un `vi.fn()`:

```ts
const mockTransaction = { execute: vi.fn() };
const command = new MyCommand(mockRepo, mockTransaction as unknown as IMyOperationTransaction);

// Verificar que la transacción se invoca con los params correctos
expect(mockTransaction.execute).toHaveBeenCalledWith(expect.objectContaining({ entityId: 'abc' }));
```

La implementación concreta (`MyOperationTransaction`) se verifica en tests de integración contra una DB real o de test. No es obligatorio en proyectos sin entorno de integración configurado: documentar la omisión con justificación.

## Anti-patrones

| Anti-patrón                                              | Problema                                                                      |
| -------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `db.transaction()` anidado                               | Drizzle no soporta savepoints; puede causar comportamiento inesperado         |
| Lógica de negocio dentro de `db.transaction()`           | Mantiene locks por más tiempo; mezlca capas                                   |
| Transacción sin que haya riesgo real de inconsistencia   | Overhead sin beneficio                                                        |
| Compensación manual (crear + borrar en caso de error)    | Propenso a race conditions y orphaned records — ver bug fix commit 692f1847   |
| Leer dentro de la transacción cuando puede hacerse antes | Extiende la duración del lock innecesariamente                                |
| Singleton de transacción (instancia compartida)          | Las transacciones son stateful; crear siempre una nueva instancia de la clase |

## Referencia canónica

`PaymentVerificationTransaction` — patrón completo con interfaz, implementación y test del command:

- Interfaz: `server/src/application/ports/IPaymentVerificationTransaction.ts`
- Implementación: `server/src/infrastructure/persistence/postgres/transactions/PaymentVerificationTransaction.ts`
- Test del command: `server/src/__tests__/unit/VerifyPaymentCommand.test.ts`

## Checklist — ¿necesito transacción?

```
¿Escribo en 2 o más tablas en la misma operación?
├── SÍ → ¿deben quedar ambas o ninguna?
│   ├── SÍ → USAR db.transaction()
│   └── NO → evaluar si la inconsistencia es aceptable
└── NO → no usar transacción

¿Uso el patrón "crear A, luego crear B, borrar A si B falla"?
└── SÍ → REEMPLAZAR con db.transaction() (es compensación manual — ver anti-patrones)

¿La operación es solo lectura?
└── SÍ → no usar transacción

¿La implementación vive en un command con lógica de negocio compleja?
└── SÍ → crear interfaz en application/ports/ + clase en transactions/
    └── NO (repositorio simple) → método atómico dentro del repositorio
```
