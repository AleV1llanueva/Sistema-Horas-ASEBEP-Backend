from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

class RegistrarMultaInput(BaseModel):
    num_cuenta: str
    actividad_id: int
    motivo: str
    monto: int

    @field_validator("motivo")
    @classmethod
    def validar_motivo(cls, v):
        if not v or not v.strip():
            raise ValueError("El motivo no puede estar vacío")
        return v.strip()

    @field_validator("monto")
    @classmethod
    def validar_monto(cls, v):
        if v <= 0:
            raise ValueError("El monto de la multa debe ser mayor a 0")

    

class MultaResponse(BaseModel):
    id: int
    num_cuenta: str
    actividad_id: int
    motivo: str
    monto: int 
    pagada: bool
    fecha_multa: datetime

    class Config: 
        from_atrributes = True