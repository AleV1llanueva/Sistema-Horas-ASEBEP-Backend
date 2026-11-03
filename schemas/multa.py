from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime, date

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
        return v


class MultaResponse(BaseModel):
    id: int
    num_cuenta: str
    actividad_id: int
    motivo: str
    monto: int 
    pagada: bool
    fecha_multa: datetime

    class Config:
        from_attributes = True


class MultaAdminResponse(MultaResponse):
    """
    Multa vista por el panel administrativo.

    Incluye datos ya resueltos para evitar cruces en el cliente.
    Los campos pueden venir vacíos si el registro relacionado falta.
    """
    nombre_estudiante: Optional[str] = None
    titulo_actividad: Optional[str] = None


class InscritoActividadResponse(BaseModel):
    """Inscrito de una actividad, usado al registrar una multa."""
    num_cuenta: str
    nombre_estudiante: Optional[str] = None
    check_in: bool
    check_out: bool
    estado: str
    multa_registrada: bool = False


class ActividadInscritosResponse(BaseModel):
    """Actividad con sus inscritos para el alta de multas."""
    actividad_id: int
    titulo: Optional[str] = None
    fecha_actividad: Optional[date] = None
    inscritos: list[InscritoActividadResponse] = []