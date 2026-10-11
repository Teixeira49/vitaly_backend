---
name: storage
description: >
  Patrón para uploads, archivos y signed URLs sobre DigitalOcean Spaces (S3):
  inyección por constructor del DigitalOceanStorageService, naming conventions
  de S3 keys y persistencia de fileUrl. Usar cuando se agregue un upload nuevo
  o se acceda a archivos en object storage.
metadata:
  owner: estei-empresas
  format: agent-skills-v1
---

# Storage — Uploads y Archivos

## Servicio principal

`DigitalOceanStorageService` vive en `server/src/infrastructure/storage/DigitalOceanStorageService.ts`.

**No existe singleton global**: el servicio se instancia por constructor con un default. El patrón correcto es inyectar por constructor para permitir mock en tests:

```ts
constructor(
  storageService: DigitalOceanStorageService = new DigitalOceanStorageService()
) {
  this.storageService = storageService;
}
```

Nunca instanciar dentro de un método (`new DigitalOceanStorageService()` dentro de un handler es anti-patrón).

## Naming conventions — rutas S3

El `fileUrl` que devuelve `executeUpload` es la **S3 key** (no una URL pública). Se persiste tal cual en la DB.

| Scope                       | Patrón                                                                                         |
| --------------------------- | ---------------------------------------------------------------------------------------------- |
| Documento de cliente        | `clients/{clientId}/documents/{documentType}/{timestamp}_{random}_{name}{ext}`                 |
| Documento de empresa        | `clients/{clientId}/companies/{companyId}/documents/{documentType}/{...}`                      |
| Documento empresa + depto   | `clients/{clientId}/companies/{companyId}/departments/{deptId}/documents/{documentType}/{...}` |
| Comprobante de pago         | `clients/{clientId}/payments/{paymentId}/proof-{timestamp}-{random}{ext}`                      |
| Retención (withholding)     | `clients/{clientId}/invoices/{invoiceId}/withholding-certificates/{IVA\|ISLR}/{...}`           |
| Solicitud de acceso         | `access-requests/{requestId}/documents/{documentType}/{...}`                                   |
| Foto de perfil              | `users/{userId}/profile/{timestamp}_{random}{ext}`                                             |
| Documentos plataforma ESTEI | `platform/estei-fiscal/documents/{documentType}/{...}`                                         |

El nombre seguro se construye como `{timestamp}_{8-bytes-hex}_{sanitizedBaseName}{ext}`. El `sanitizedBaseName` reemplaza caracteres no alfanuméricos con `_` y se trunca a 50 chars.

## Cómo subir un archivo

1. Configurar multer con `memoryStorage()` y límite de 10 MB en la ruta.
2. Llamar `storageService.validateFile(file, documentType)` antes de subir; si no es válido, responder 400.
3. Llamar el método específico según el scope (e.g. `uploadClientDocument`, `uploadCompanyDocument`).
4. El resultado contiene `{ fileName, fileUrl, fileSize, mimeType }`. El `fileUrl` es la **S3 key**.
5. Persistir el registro en DB. Si la inserción falla, llamar `storageService.deleteFile(uploadResult.fileUrl)` para evitar archivos huérfanos en S3.

## URLs: signed vs CDN

Todos los archivos se suben con `ACL: 'private'`. No existe URL pública directa.

| Caso de uso                           | Método                                               | TTL default   |
| ------------------------------------- | ---------------------------------------------------- | ------------- |
| Ver/abrir archivo en browser          | `generateSignedUrl(s3Key, seconds?)`                 | 3600 s (1 h)  |
| Forzar descarga (Content-Disposition) | `generateDownloadUrl(s3Key, originalName, seconds?)` | 300 s (5 min) |

El `fileUrl` guardado en DB es la S3 key, no una URL firmada. Generar la URL firmada en el momento de servir el recurso, nunca persistirla.

## Validación

`validateFile(file, documentType)` aplica:

- **Tamaño máximo**: 10 MB para documentos, 5 MB para imágenes de perfil (`validateProfileImage`).
- **MIME types por documentType**:
  - `RIF`, `CONSTITUTIVE`, `POWER_OF_ATTORNEY` → solo `application/pdf`
  - `OTHER` → `application/pdf`, `image/jpeg`, `image/png`, `.doc`, `.docx`
  - Comprobantes de pago y retenciones → `application/pdf`, `image/jpeg`, `image/png`
  - Fotos de perfil → `image/jpeg`, `image/png`, `image/gif`, `image/webp`
- **Extensión vs MIME**: verifica que la extensión del archivo coincida con el MIME type declarado.

Algunos métodos de upload tienen validación interna propia (`uploadPaymentProof`, `uploadWithholdingCertificate`). Igualmente llamar `validateFile` antes en el controller.

## Entorno de desarrollo

Si `DO_SPACES_ACCESS_KEY` o `DO_SPACES_SECRET_KEY` no están configurados, `this.s3Client` es `null`. En ese caso:

- Cada método de upload retorna un `FileUploadResult` con una URL falsa tipo `https://dev.example.com/...`.
- `deleteFile` retorna `true` sin hacer nada.
- `generateSignedUrl` y `generateDownloadUrl` retornan una URL fake.
- El servicio loguea el intento en modo `info` con prefijo `[DEV]` o `DEV mode:`.

No lanzar errores en dev por falta de credenciales. El flujo completo funciona de extremo a extremo sin S3 real.

## Anti-patrones

- **`new DigitalOceanStorageService()` dentro de un método handler** → imposible de mockear en tests.
- **Asumir que `fileUrl` es una URL pública** → es una S3 key privada; siempre generar URL firmada para servir.
- **Persistir URLs firmadas en DB** → expiran; persistir solo la S3 key.
- **No limpiar S3 si falla el insert en DB** → archivos huérfanos; siempre hacer rollback con `deleteFile`.
- **Saltarse `validateFile` confiando en multer** → multer solo filtra por tamaño; la validación de MIME y extensión la hace el servicio.
- **Instanciar el servicio sin inyección** → rompe los tests unitarios que necesitan mock.

## Referencia canónica

`server/src/infrastructure/web/express/controllers/ClientDocumentController.ts`

Muestra el patrón completo: inyección por constructor con default, `validateFile` antes de subir, rollback con `deleteFile` si falla el DB insert, y multer configurado como middleware exportado.

## Checklist — antes de agregar un nuevo flujo de upload

- [ ] ¿El controller recibe `storageService` por constructor (con default `new`)? ¿Está mockeado en el test?
- [ ] ¿Se llama `validateFile` o `validateProfileImage` antes de subir?
- [ ] ¿La S3 key sigue el naming convention del scope correspondiente?
- [ ] ¿Se persiste la S3 key (no una URL firmada) en la DB?
- [ ] ¿Hay rollback con `deleteFile` si el insert en DB falla?
- [ ] ¿Las URLs firmadas se generan en el momento de servir, no al subir?
- [ ] ¿El multer está configurado con `memoryStorage()` y límite de 10 MB?
