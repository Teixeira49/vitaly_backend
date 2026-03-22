from enum import Enum

class UserRole(str, Enum):
    ADMIN_SISTEMA = "admin_sistema"
    ADMIN_ESCUELA = "admin_escuela"
    DOCTOR = "doctor"
    REPRESENTANTE = "representante"

class Gender(str, Enum):
    MASCULINO = "MASCULINO"
    FEMENINO = "FEMENINO"

class BloodType(str, Enum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"
