import re
import os
from pydantic import BaseModel, field_validator
from typing import Optional
from dotenv import load_dotenv

from schemas.becario import PerfilBecarioResponse

load_dotenv()

DOMINIO_PERMITO = os.getenv("DOMINIO_CORREO", "unah.hn")

class CrearUsuario(BaseModel):
    """
        Define qué datos recibe el endpoint cuando el admin crea un usuario.
    """
    num_cuenta: str
    primer_nombre: str
    segundo_nombre: Optional[str] = None
    primer_apellido: str
    segundo_apellido: Optional[str] = None 
    correo_institucional: str
    correo_personal: str
    telefono: str
    carrera_id: int
    rol_id: int
    mes_inicio: int
    anio_inicio: int

    @field_validator("num_cuenta")
    @classmethod
    def validar_num_cuenta(cls, v):
        if not re.match(r"^\d{11}$", v):
            raise ValueError("El número de cuenta debe tener exactamente 11 digitos")
        return v

    @field_validator("correo_institucional")
    @classmethod
    def validar_correo(cls, v):
        if not v.endswith(f"@{DOMINIO_PERMITO}"):
            raise ValueError("El correo debe ser institucional @unah.hn")
        return v.lower().strip()

    @field_validator("primer_nombre", "primer_apellido")
    @classmethod
    def validar_no_vacio(cls, v):
        if not v or not v.strip():
            raise ValueError("Este campo no puede estar vacío")
        return v.strip()

    @field_validator("mes_inicio")
    @classmethod
    def validar_mes(cls, v):
        if v < 1 or v > 12:
            raise ValueError("El mes debe estar entre 1 y 12")
        return v

    @field_validator("anio_inicio")
    @classmethod
    def validar_anio(cls, v):
        from datetime import date
        if v < 2000 or v > date.today().year:
            raise ValueError("El año de inicio no es válido")
        return v

class UsuarioResponse(BaseModel):
    """
        Define qué se le devuelve al admin después de crear el usuario exitosamente. 
    """
    num_cuenta: str
    primer_nombre: str
    primer_apellido: str
    correo_institucional: str
    rol_id: int
    active: bool 
    perfil_becario: Optional[PerfilBecarioResponse] = None

