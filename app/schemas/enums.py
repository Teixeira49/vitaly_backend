from enum import Enum


class UserRole(str, Enum):
    """Roles del sistema. Determinan el gate `get_current_*` que protege cada ruta."""

    ADMIN_SISTEMA = "admin_sistema"
    ADMIN_ESCUELA = "admin_escuela"
    DOCTOR = "doctor"
    REPRESENTANTE = "representante"


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
