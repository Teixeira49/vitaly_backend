---
title: "[🐛 Bug] IMC sin conversión cm→m en detalle de representante"
labels: [bug, P2, services]
issue: 21
url: https://github.com/Teixeira49/vitaly_backend/issues/21
---

## Descripción
El detalle de un representante (`GET /api/v1/school-admin/representatives/{parent_id}`) calcula el IMC de cada estudiante vinculado con la altura en centímetros sin convertirla a metros. El valor resultante es del orden de 0.001, siempre menor que 18.5, por lo que todo estudiante con métricas aparece como `DESNUTRIDO`. Los demás cálculos de IMC del mismo servicio usan el helper `_calculate_bmi`, que sí convierte.

## Evidencia
- `app/services/school_admin_service.py:1428-1430` — `bmi = weight / (height ** 2)` con `height` leído directamente de `student_metrics`, sin dividir entre 100.
- `app/services/school_admin_service.py:52-61` — `_calculate_bmi(weight_kg, height_cm)` documenta la altura en cm y la convierte (`height_cm / 100.0`).
- `app/services/school_admin_service.py:260`, `:447`, `:566` — los otros tres cálculos pasan el mismo campo `height` de `student_metrics` a `_calculate_bmi`.
- `app/services/school_admin_service.py:1436` — esta rama clasifica el tercer rango como `OBESO`, mientras que `:454` usa `SOBREPESO` para el mismo rango.
- Unidad de `student_metrics.height`: se asume cm por `_calculate_bmi` y porque el frontend la muestra en cm (`StudentProfile.tsx`, `pdfGenerator.ts`). No se verificó contra datos reales; confirmarlo forma parte del fix.
- Ejemplo con datos sintéticos: peso 30 kg y altura 130 cm → `30 / 130² ≈ 0.0018` → `DESNUTRIDO`; el valor correcto es `30 / 1.30² ≈ 17.75`.
- Reproducción: `grep -n "weight / (height \*\* 2)" app/services/school_admin_service.py`.

## Comportamiento actual vs esperado
- **Actual:** todo estudiante con métricas figura como `DESNUTRIDO` en el detalle del representante, y la etiqueta del rango superior (`OBESO`) difiere del resto del servicio.
- **Esperado:** el IMC se calcula con `_calculate_bmi` y la clasificación coincide con la de los demás endpoints del servicio.

## Impacto
- ¿Expone datos médicos/PHR o PII? No hay exposición, pero se muestra un estado nutricional **incorrecto** de menores, lo que puede inducir decisiones erróneas del personal escolar.
- ¿Fuga entre escuelas (school_id)? No.
- Roles afectados: `admin_escuela`.

## Propuesta de solución
Sustituir el cálculo en línea por `self._calculate_bmi(weight, height)` y extraer la clasificación (actualmente duplicada en `:262`, `:449`, `:569` y `:1430`) a un único helper, unificando las etiquetas.

Pregunta abierta, fuera del alcance de este bug: los cortes actuales (18.5 / 24.9) son umbrales OMS para adultos; en estudiantes corresponde IMC para la edad (percentiles). Se propone tratarlo en un issue aparte.

## Criterios de aceptación
- [ ] `get_parent_detail` usa `_calculate_bmi`; con peso 30 kg y altura 130 cm el estado no es `DESNUTRIDO`.
- [ ] La clasificación por IMC vive en un único helper reutilizado en los cuatro puntos.
- [ ] Las etiquetas de estado nutricional son las mismas en todos los endpoints.
- [ ] Test en `tests/` que cubre el cálculo y la clasificación con datos sintéticos.

## Referencias
- Rol `.agents/roles/medical-domain-agent.md` (deuda técnica de clasificación duplicada).
- Skill `vitaly-feature-testing`.
