# 🏥 Investigación de Arquitectura: Servicios Recomendados para el Backend de Vitaly

**Fecha:** Septiembre 2026  
**Versión de API base:** v0.4.0+  
**Objetivo:** Analizar e identificar servicios e integraciones complementarias para potenciar el backend de Vitaly, considerando su stack actual, el dominio de salud escolar, la protección de datos médicos de menores (PII/PHR) y la arquitectura multi-tenant.

---

## 1. Diagnóstico del Stack Actual

Actualmente, el backend de **Vitaly** se encuentra estructurado con las siguientes bases técnicas:

* **Framework Web:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+) con tipado fuerte vía [Pydantic v2](https://docs.pydantic.dev/).
* **Base de Datos & Autenticación:** [Supabase](https://supabase.com/) (PostgreSQL + PostgREST + Auth/JWT + Token Blacklist en base de datos).
* **Almacenamiento Multimedia:** [ImageKit.io](https://imagekit.io/) (`imagekitio`) para fotos de perfil y multimedia de usuarios, doctores y administradores.
* **Patrones de Arquitectura:**
  * Capa de servicios (`app/services/*`) y routers versionados (`app/api/v1/endpoints/*`).
  * Respuestas estandarizadas mediante `APIResponse[T]`.
  * Multi-tenancy silencioso y estricto por `school_id` resuelto desde el JWT.
  * Suite de pruebas unitarias y de integración con `pytest` y dobles de prueba en memoria.

---

## 2. Servicios Recomendados para Incorporación

---

### 🔔 1. Sistema de Notificaciones Transaccionales y Alertas (Email & WhatsApp / SMS)
> **Prioridad:** 🔴 Alta (Crítica para el flujo de salud escolar)

#### 💡 ¿Qué es y para qué sirve? (Definición no técnica)
Es el canal de comunicación que permite a la plataforma enviar avisos y mensajes directos a las personas cuando ocurre un suceso importante. Sirve para mantener comunicados a los representantes, colegios y médicos en tiempo real, asegurando que reciban información crítica (como emergencias de salud de sus hijos o citas programadas) a través de su correo electrónico o su teléfono móvil sin necesidad de que estén revisando la aplicación constantemente.

#### 🎯 Justificación en el Dominio de Vitaly:
* **Alertas de incidentes clínicos:** Si un estudiante presenta fiebre alta, traumatismos, crisis asmáticas o alergias repentinas durante la jornada escolar, los representantes deben ser notificados de inmediato.
* **Operaciones de plataforma:** Envío de invitaciones a doctores o directores de escuela, restablecimiento seguro de credenciales y activación de cuentas.
* **Jornadas escolares y eventos de salud:** Recordatorios de jornadas de vacunación, pesaje o chequeos anuales vinculados al módulo de eventos (`app/api/v1/endpoints/school_admin_events.py`).

#### 🛠️ Soluciones Recomendadas:
* **Email Transaccional:**
  * **Resend** o **Postmark**: Alta entregabilidad, SDK nativo en Python, soporte para plantillas HTML dinámicas y analítica de entrega.
* **Mensajería Instantánea (WhatsApp / SMS):**
  * **Twilio** o **Meta WhatsApp Cloud API**: En el ámbito educativo de Latinoamérica y España, WhatsApp es uno de los canales más usados por los padres, por lo que se espera una tasa de apertura superior a la del correo electrónico.

#### 🌐 Otras Opciones (Servicios Alternativos):
* [SendGrid](https://sendgrid.com/)
* [Brevo (anteriormente Sendinblue)](https://www.brevo.com/)
* [OneSignal](https://onesignal.com/)
* [Courier](https://www.courier.com/)
* [MessageBird / Bird](https://bird.com/)
* [Amazon SES](https://aws.amazon.com/ses/)
* [Mailgun](https://www.mailgun.com/)

---

### 📄 2. Generador de Documentos y Reportes Médicos (PDF Service)
> **Prioridad:** 🔴 Alta (Requisito operativo de instituciones y familias)

#### 💡 ¿Qué es y para qué sirve? (Definición no técnica)
Es la herramienta que toma los datos registrados en el sistema (como las consultas, vacunas, peso, talla o diagnósticos de un estudiante) y los transforma automáticamente en un documento digital con formato oficial e imprimible (PDF). Sirve para que padres y directores puedan descargar, imprimir, guardar o presentar físicamente constancias médicas escolares con validez institucional.

#### 🎯 Justificación en el Dominio de Vitaly:
* **Ficha Médica Escolar:** Resumen clínico oficial del estudiante (tipo de sangre, alergias, diagnósticos, historial de vacunas y contactos de emergencia).
* **Consentimiento Informado:** Documento legal que autoriza a los doctores de la institución a realizar chequeos clínicos periódicos al menor.
* **Reporte de Evolución y Curvas de Crecimiento:** Informes con evolución de peso, talla y percentiles de IMC (Índice de Masa Corporal) para entrega al final del ciclo escolar.

#### 🛠️ Soluciones Recomendadas:
* **WeasyPrint** (renderizado HTML/CSS a PDF en Python) o **Gotenberg** (microservicio dockerizado basado en headless Chromium).
* Motor de plantillas **Jinja2 + Tailwind/HTML** para maquetar documentos limpios y brandeados con el logo de Vitaly y de cada colegio.
* Almacenamiento seguro del PDF resultante en Supabase Storage o entrega en streaming con URLs temporales firmadas.

#### 🌐 Otras Opciones (Servicios Alternativos):
* [DocRaptor](https://docraptor.com/)
* [PDFShift](https://pdfshift.io/)
* [APITemplate.io](https://apitemplate.io/)
* [Puppeteer](https://pptr.dev/)
* [Browserless](https://www.browserless.io/)
* [ReportLab](https://www.reportlab.com/)
* [Html2Pdf Rocket](https://www.html2pdfrocket.com/)

---

### ⚙️ 3. Cola de Tareas Asíncronas y Tareas Programadas (Workers / Background Jobs)
> **Prioridad:** 🔴 Alta (Escalabilidad y desacoplamiento)

#### 💡 ¿Qué es y para qué sirve? (Definición no técnica)
Funciona como un asistente virtual que realiza trabajos pesados "tras bambalinas". Sirve para que la plataforma no se congele ni haga esperar a los usuarios cuando se deben procesar cientos de registros a la vez, generar documentos complejos o realizar labores automáticas a horas fijas (como cerrar un año escolar a medianoche o enviar resúmenes semanales).

#### 🎯 Justificación en el Dominio de Vitaly:
* **Operaciones pesadas en segundo plano:** La matriculación masiva (`BulkClassroomRegistrationCreate`), el procesamiento de hojas de cálculo o la generación de PDFs pueden demorarse varios segundos y no deben bloquear el hilo de respuesta de FastAPI.
* **Tareas periódicas (Cron jobs):**
  * Cierre y apertura programada de años académicos.
  * Recordatorios automáticos de casos médicos abiertos o no resueltos.
  * Resúmenes estadísticos semanales/mensuales para los directores escolares.

#### 🛠️ Soluciones Recomendadas:
* **Redis + ARQ** (asíncrono, basado en `asyncio`, de bajo consumo y muy amigable con FastAPI) o **Celery** (si se requieren flujos de trabajo orquestados más complejos).
* *Alternativa serverless nativa:* Extensión `pg_cron` de PostgreSQL en Supabase combinada con llamadas vía webhooks / Edge Functions.

#### 🌐 Otras Opciones (Servicios Alternativos):
* [TaskIQ](https://taskiq-python.github.io/)
* [BullMQ](https://bullmq.io/)
* [RabbitMQ](https://www.rabbitmq.com/)
* [Dramatiq](https://dramatiq.io/)
* [Temporal](https://temporal.io/)
* [Inngest](https://www.inngest.com/)
* [Upstash Redis](https://upstash.com/redis)

---

### 🛡️ 4. Trazabilidad y Registro de Auditoría Médica (Audit Logging / PHR)
> **Prioridad:** 🟡 Media - Alta (Cumplimiento legal y normativo)

#### 💡 ¿Qué es y para qué sirve? (Definición no técnica)
Es como una bitácora o "cámara de seguridad digital" que anota de manera permanente e inalterable cada acción realizada sobre información sensible. Sirve para saber con certeza total qué persona abrió, leyó o modificó la historia médica de un menor, a qué hora exacta lo hizo y desde qué computadora, protegiendo legalmente tanto al colegio como a la plataforma ante cualquier sospecha o reclamo sobre el uso indebido de datos de salud.

#### 🎯 Justificación en el Dominio de Vitaly:
* La información médica de menores de edad es de carácter ultra sensible (**PII/PHR**).
* Para cumplir con normativas de protección de datos personales y de salud, es mandatorio contar con un registro inmutable que responda:
  * *¿Quién (user_id) consultó o modificó la historia clínica del alumno X?*
  * *¿Cuándo ocurrió el acceso y desde qué dirección IP?*
  * *¿Cuál fue el cambio aplicado?*

#### 🛠️ Soluciones Recomendadas:
* Middleware de auditoría en FastAPI o tabla dedicada `audit_log` en PostgreSQL con triggers automáticos (`pg_audit` o Supabase `audit.record_version`).

#### 🌐 Otras Opciones (Servicios Alternativos):
* [WorkOS Audit Logs](https://workos.com/docs/audit-logs)
* [Datadog Cloud SIEM](https://www.datadoghq.com/product/cloud-siem/)
* [Logflair](https://logflair.com/)
* [AWS CloudTrail](https://aws.amazon.com/cloudtrail/)
* [Pangea Audit](https://pangea.cloud/services/audit/)

---

### 📊 5. Observabilidad, Monitoreo y Manejo de Excepciones
> **Prioridad:** 🟡 Media (Operatividad y estabilidad)

#### 💡 ¿Qué es y para qué sirve? (Definición no técnica)
Es el panel de control y alarma técnica de la aplicación. Sirve para vigilar constantemente que el sistema funcione a buena velocidad y sin caídas, notificando de inmediato a los desarrolladores en el mismo segundo en que ocurre un fallo técnico o una falla de conexión, permitiendo solucionarlo antes de que los médicos, directivos o padres de familia se den cuenta.

#### 🎯 Justificación en el Dominio de Vitaly:
* Actualmente el sistema depende de `logging` en consola y el endpoint `/health-visual`.
* En un entorno de producción con múltiples escuelas activas, es crucial detectar fallos de conectividad con Supabase o ImageKit antes de que impacten a los usuarios.

#### 🛠️ Soluciones Recomendadas:
* **Sentry (FastAPI SDK):** Monitoreo de errores no controlados, trazabilidad de llamadas a servicios externos, latencia de endpoints y captura del contexto de la petición (sin comprometer datos sensibles).
* **Logging Estructurado:** Integración con **Loguru** o formato JSON estándar para exportar métricas hacia plataformas centralizadas.

#### 🌐 Otras Opciones (Servicios Alternativos):
* [Better Stack](https://betterstack.com/)
* [Datadog](https://www.datadoghq.com/)
* [New Relic](https://newrelic.com/)
* [Grafana Cloud](https://grafana.com/products/cloud/)
* [LogRocket](https://logrocket.com/)
* [Uptime Kuma](https://uptime.kuma.pet/)
* [GlitchTip](https://glitchtip.com/)

---

### 📥 6. Motor de Importación Masiva (Excel / CSV)
> **Prioridad:** 🟡 Media (Facilidad de onboarding de colegios)

#### 💡 ¿Qué es y para qué sirve? (Definición no técnica)
Es la función que permite cargar listas gigantescas de personas o salones desde un archivo de Excel con un solo clic. Sirve para que el personal del colegio no tenga que registrar a cientos o miles de alumnos uno a uno a mano, verificando automáticamente que las cédulas, fechas y datos no vengan equivocados o repetidos antes de guardarlos.

#### 🎯 Justificación en el Dominio de Vitaly:
* Al inicio de cada año académico, los administradores escolares no ingresan cientos de alumnos individualmente; suben la nómina del colegio en formato `.xlsx` o `.csv`.

#### 🛠️ Soluciones Recomendadas:
* **Polars** u **OpenPyXL**: Procesamiento rápido en memoria con validación registro a registro mediante esquemas Pydantic (`StudentCreate`), devolviendo un reporte con registros exitosos y líneas con inconsistencias (cédulas duplicadas, formatos inválidos).

#### 🌐 Otras Opciones (Servicios Alternativos):
* [Flatfile](https://flatfile.com/)
* [UseCSV](https://usecsv.com/)
* [Pandas](https://pandas.pydata.org/)
* [Dask](https://www.dask.org/)
* [XlsxWriter](https://xlsxwriter.readthedocs.io/)
* [DatoCMS CSV Importer](https://www.datocms.com/)

---

### 🔍 7. Búsqueda Médica Avanzada (Full-Text Search y Trigramas)
> **Prioridad:** 🟢 Media - Baja (Optimizaciones futuras)

#### 💡 ¿Qué es y para qué sirve? (Definición no técnica)
Es un buscador inteligente (similar a Google) dentro del sistema. Sirve para encontrar inmediatamente a un estudiante, una enfermedad o un medicamento, incluso si la persona que lo busca no recuerda el nombre exacto o comete faltas de ortografía y errores de escritura al teclear.

#### 🎯 Justificación en el Dominio de Vitaly:
* Búsqueda ágil y tolerante a errores tipográficos sobre nombres de alumnos, diagnósticos, patologías y catálogos de salud (ej. clasificaciones CIE-10 / ICD-10).
* Estado actual: las búsquedas de `school_admin_service.py` usan `ilike` (coincidencia parcial sin tolerancia a errores tipográficos); `pg_trgm` sería la evolución natural de ese enfoque.

#### 🛠️ Soluciones Recomendadas:
* Extensión nativa de PostgreSQL **`pg_trgm`** y soporte para búsqueda por texto completo (`tsvector`), aprovechando las capacidades nativas de PostgreSQL en Supabase sin necesidad de desplegar motores externos.

#### 🌐 Otras Opciones (Servicios Alternativos):
* [Meilisearch](https://www.meilisearch.com/)
* [Typesense](https://typesense.org/)
* [Algolia](https://www.algolia.com/)
* [Elasticsearch](https://www.elastic.co/)
* [OpenSearch](https://opensearch.org/)

---

## 3. Matriz de Priorización y Retorno de Inversión (ROI)

| Servicio / Componente | Tecnologías Recomendadas | Caso de Uso en Vitaly | ROI / Impacto |
| :--- | :--- | :--- | :--- |
| **Notificaciones y Alertas** | Resend (Email) + Twilio / WhatsApp API | Alertas médicas urgentes a padres, citas e invitaciones | ⭐⭐⭐⭐⭐ (Inmediato) |
| **Reportes Clínicos en PDF** | Jinja2 + WeasyPrint / Gotenberg | Ficha médica escolar, certificados de salud y consentimientos | ⭐⭐⭐⭐⭐ (Esencial) |
| **Cola de Tareas Asíncronas** | Redis + ARQ (o TaskIQ) | Carga masiva de alumnos, generación de PDFs en segundo plano | ⭐⭐⭐⭐ (Rendimiento) |
| **Auditoría de Salud (PHR)** | Tabla `audit_log` / Postgres Triggers | Trazabilidad legal de accesos a expedientes de menores | ⭐⭐⭐⭐ (Compliance) |
| **Monitoreo & Sentry** | Sentry SDK para FastAPI | Detección preventiva de errores e incidentes en producción | ⭐⭐⭐⭐ (Operaciones) |
| **Importador Masivo Excel** | Polars / OpenPyXL + Pydantic | Onboarding veloz de planteles y salones al iniciar el año | ⭐⭐⭐ (Operatividad) |
| **Búsqueda Avanzada** | Postgres `pg_trgm` en Supabase | Tolerancia a errores de tipeo en búsquedas clínicas | ⭐⭐⭐ (UX) |

---

## 4. Hoja de Ruta Sugerida (Roadmap)

### Fase 1: Valor Inmediato a Familias y Colegios (Próximo Sprint)
1. **Servicio de Fichas Médicas (PDF):** Integrar generador de PDF con plantilla Jinja2 para la Ficha Médica Escolar y resumen de casos médicos.
2. **Servicio de Notificaciones (Email/WhatsApp):** Integrar un cliente para envío transaccional (ej. Resend) para alertas clínicas y bienvenida a usuarios.

### Fase 2: Robustez Operativa y Carga de Datos
1. **Cola Asíncrona (Redis + ARQ):** Mover tareas lentas (generación de PDFs pesados y envíos masivos) a workers independientes.
2. **Importador de Alumnos (Excel/CSV):** Endpoint de carga masiva de salones y nóminas escolares.

### Fase 3: Seguridad, Auditoría y Observabilidad
1. **Sentry & Logs Estructurados:** Monitoreo activo de la plataforma.
2. **Audit Logging de Historias Médicas:** Registro inmutable de consultas clínicas a registros de menores de edad.
