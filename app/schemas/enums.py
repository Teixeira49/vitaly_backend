from enum import Enum

class UserRole(str, Enum):
    ADMIN_SISTEMA = "admin_sistema"
    ADMIN_ESCUELA = "admin_escuela"
    DOCTOR = "doctor"
    REPRESENTANTE = "representante"
