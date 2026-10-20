from enum import Enum


class UserRole(str, Enum):
    """Roles del sistema. Determinan el gate `get_current_*` que protege cada ruta."""

    ADMIN_SISTEMA = "admin_sistema"
    ADMIN_ESCUELA = "admin_escuela"
    DOCTOR = "doctor"
    REPRESENTANTE = "representante"


class TokenScope(str, Enum):
    """Procedencia de un JWT: el portal de login que lo emitió (claim `scope`)."""
    ADMIN = "admin"
    CLIENT = "client"

# Roles que cada portal de login acepta. Un rol pertenece a un único scope.
SCOPE_ROLES: dict[TokenScope, frozenset[UserRole]] = {
    TokenScope.ADMIN: frozenset({UserRole.ADMIN_SISTEMA}),
    TokenScope.CLIENT: frozenset({UserRole.ADMIN_ESCUELA, UserRole.DOCTOR, UserRole.REPRESENTANTE}),
}

class Gender(str, Enum):
    """Género registrado de un estudiante."""

    MASCULINO = "MASCULINO"
    FEMENINO = "FEMENINO"


class BloodType(str, Enum):
    """Tipo de sangre del estudiante en notación ABO/Rh."""

    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"
