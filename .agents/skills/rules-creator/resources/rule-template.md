---
description: "Descripción breve y de alta señal: qué impone la regla y cuándo debe aplicarla el agente"
globs:
  - "app/api/**/*.py"
alwaysApply: false
---

# [Título de la regla / Dominio]

## 1. Scope & Context
- **Target Area:** [Módulos, archivos o capas afectadas]
- **Roles:** [Backend Architect | Security Sentinel | Database Specialist | Medical Domain Guardian]
- **Objetivo:** [1-2 frases sobre por qué existe la regla]
- **Guía práctica:** [Skill que contiene el "cómo", si existe, ej. `vitaly-rbac`]

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** [acción que rompe integridad, multi-tenancy o seguridad]
- ⛔ **NUNCA** [antipatrón común a prevenir]
- 🔒 **MANDATORIO:** [requisito base que siempre debe cumplirse]

## 3. Directivas Prescriptivas
1. **[Acción 1]:** Usa [patrón A] en lugar de [patrón B] cuando [escenario].
2. **[Acción 2]:** Declara explícitamente [tipos/esquemas/dependencias].
3. **[Acción 3]:** Maneja los fallos con [excepción o estrategia concreta].

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
```python
# Mal: falta la restricción, el tipo o la validación requerida
def example_bad():
    pass
```

### ✅ Patrón Estándar (DO)
```python
# Bien: muestra la restricción explícita, los tipos correctos y el patrón aprobado
def example_good():
    pass
```

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] Restricción A verificada
  - [ ] Tipos y esquemas coinciden
- **Comando de Verificación:** `pytest tests/...` o `ruff check app/`
