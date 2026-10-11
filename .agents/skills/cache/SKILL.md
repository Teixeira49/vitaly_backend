---
name: cache
description: >
  Define el uso correcto del Redis distribuido en `server/src/infrastructure/cache/`
  (RedisService singleton). Reglas no negociables: timeouts agresivos para cumplir
  NFR vs Estei API y graceful degradation silenciosa cuando Redis cae. Usar al
  consumir, modificar o agregar lógica que dependa de Redis.
metadata:
  owner: estei-empresas
  format: agent-skills-v1
---

# Cache — Redis Distribuido

## Cuándo usar este skill

- Consumir o agregar caché distribuida (compartida entre instancias).
- Tocar `server/src/infrastructure/cache/RedisService.ts` o sus consumidores.
- Cambiar timeouts, retries o lifecycle de Redis.
- Agregar nuevos servicios que necesiten persistencia efímera fuera del proceso.
- Revisar manejo de errores cuando Redis está caído.

## No usar este skill para

- Caché LRU **in-memory** del motor de búsqueda → `search-architecture`.
- Pool de PostgreSQL/Drizzle → `database-connections`.
- Logging del servicio → `logging`.

## RedisService

Singleton wrapper sobre `ioredis`. Diseño documentado en la decisión `issue-490-perf-v2`.

### Acceso

```ts
import { redisService } from '../infrastructure/cache/RedisService';
// o desde composition-root:
import { redisService } from '../composition-root';
```

No instancies `RedisService` ni `new Redis()` en otro lado. El singleton lo expone también `composition-root.ts`.

### Configuración (env vars)

Definidas y validadas en `ConfigurationService.ts`:

- `REDIS_HOST` — default `localhost`.
- `REDIS_PORT` — default `6379`.
- `REDIS_PASSWORD` — opcional.

No existe `REDIS_URL`. Si necesitas agregar una, hazlo en `ConfigurationService` con su schema Zod, no inline en `RedisService`.

### Lifecycle

- `await redisService.connect()` se llama una vez en `server/index.ts` durante el startup, **non-blocking**: si Redis no está disponible, la app sigue corriendo con `isAvailable() === false`.
- `await redisService.disconnect()` se llama en SIGTERM/SIGINT como parte del shutdown ordenado.
- Eventos `connect`, `ready`, `reconnecting`, `error`, `end` se loguean vía `loggingService` con su `operation` correspondiente.

### Timeouts y retries (no negociables)

Constantes en `RedisService.ts`:

| Parámetro              | Valor    | Por qué                                                                            |
| ---------------------- | -------- | ---------------------------------------------------------------------------------- |
| `connectTimeout`       | `2000ms` | Falla rápido al inicializar; la app puede arrancar sin caché.                      |
| `commandTimeout`       | `500ms`  | La caché DEBE responder más rápido que Estei API (~800ms). Si tarda más, no sirve. |
| `maxRetriesPerRequest` | `1`      | Una sola reintento por comando para no apilar latencia.                            |
| `retryStrategy`        | hasta 3  | Reconexión con backoff `1s, 2s, 3s`, luego `null` (deja de intentar).              |
| `lazyConnect`          | `true`   | El connect se controla manualmente desde `connect()`.                              |

Si subes `commandTimeout`, violas el NFR del NFR-5 de `issue-490-perf-v2`: la caché pierde su razón de ser frente a Estei API. No lo toques sin coordinar con un cambio de NFR.

## Patrón obligatorio: graceful degradation silenciosa

**Regla**: si Redis falla, `get` devuelve `null`, `setex` y `del` son no-op. Nunca `throw` al caller.

Razones:

- La app debe seguir funcionando con Redis caído.
- Si el wrapper tirara, **toda** request que pase por caché caería → cascading failure.
- El retry está dentro de `ioredis` (`maxRetriesPerRequest`, `retryStrategy`). No agregues circuit breaker manual encima.

### Forma del patrón

Cada operación sigue exactamente esta estructura:

```ts
public async get(key: string): Promise<string | null> {
  if (!this.isAvailable() || !this.client) return null;
  try {
    return await this.client.get(key);
  } catch (err) {
    loggingService.error('Redis get failed', err as Error, {
      operation: 'redis_get_error',
      key,
    });
    return null;
  }
}
```

Tres reglas que siempre se cumplen:

1. Guard: `if (!this.isAvailable() || !this.client) return null;` (o `return;` para no-op).
2. Try/catch que **siempre** loguea con `loggingService.error` y retorna el fallback.
3. Cero `throw`. Cero `console.*`.

### Patrón en consumidores (bypass safe)

Cuando un consumidor depende del caché, debe degradarse igual de bien:

```ts
if (!this.redis.isAvailable()) {
  return fetcher(); // bypass total, sin tocar Redis
}
const cached = await this.redis.get(key);
if (cached) return JSON.parse(cached);
const fresh = await fetcher();
await this.redis.setex(key, ttl, JSON.stringify(fresh));
return fresh;
```

Ver `TileCacheService.getOrFetch` en `server/src/infrastructure/search/tile-cache.service.ts` como referencia.

## Cuándo usar Redis vs in-memory

| Caso                                                         | Usar                                      |
| ------------------------------------------------------------ | ----------------------------------------- |
| Datos compartidos entre instancias (multi-replica)           | Redis                                     |
| Resultados con TTL que sobreviven a despliegues parciales    | Redis                                     |
| Tile cache, fragmentos costosos de Estei API                 | Redis                                     |
| Caché local hot-path por proceso, sin necesidad de compartir | LRU in-memory                             |
| Estructuras del motor de búsqueda por request/proceso        | LRU in-memory (ver `search-architecture`) |

Si dudas, asume Redis: la mayoría del proyecto corre detrás de cargas que no toleran cachés desincronizadas entre réplicas.

## Anti-patrones

- Subir `commandTimeout` sobre `500ms` sin renegociar NFR vs Estei API.
- Reemplazar `return null` / no-op por `throw` o `Promise.reject` en el wrapper.
- Instanciar `new Redis(...)` directamente en cualquier archivo que no sea `RedisService.ts`.
- Implementar circuit breaker manual encima — `ioredis` ya maneja reconexión.
- Hacer un consumidor que falle si `redis.isAvailable() === false`. Siempre debe haber bypass.
- Loguear con `console.*` los errores de Redis. Solo `loggingService`.
- Agregar `REDIS_URL` u otras envs sin pasarlas por `ConfigurationService`.

## Tests

Convención general en `testing-convention`. Para mockear el servicio:

- Mockear `ioredis` con un `EventEmitter` que expone `get/setex/del/quit/connect` como `vi.fn()` y permite emitir `ready`, `error`, `end`, `reconnecting`. Ejemplo en `server/src/infrastructure/cache/__tests__/RedisService.test.ts`.
- Mockear `loggingService` y `configService` para aislar el test.
- Resetear el singleton entre tests: `(RedisService as any).instance = undefined;`.
- Cubrir los dos caminos críticos: Redis up (delegación al cliente) y Redis down (`null` / no-op sin throw).
- Para consumidores, inyectar un `RedisService` falso en el constructor (ver patrón en `TileCacheService.getInstance`) — todos los servicios que dependan de Redis deben aceptar inyección.

## Relación con otros skills

- `search-architecture` — describe la **caché LRU in-memory** del motor de búsqueda. Es local al proceso, no usa Redis. No mezclar.
- `database-connections` — describe el pool de **PostgreSQL/Drizzle**. No tiene relación con Redis.
- `composition-root` — `redisService` se reexporta desde ahí para que los servicios lo reciban inyectado.
- `logging` — todos los eventos y errores de Redis pasan por `loggingService`.
- `testing-convention` — base para los tests del servicio y sus consumidores.
