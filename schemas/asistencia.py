from pydantic import BaseModel
from datetime import date, time

class InscripcionInput(BaseModel):
    actividad_id: int

class InscripcionResponse(BaseModel):
    id: int
    actividad_id: int
    num_cuenta: str
    estado: str

    class Config:
        from_attributes = True

class MisInscripcionesResponse(BaseModel):
    id: int
    actividad_id: int
    titulo: str
    fecha_actividad: date
    hora_inicio: time
    hora_final: time
    ubicacion: str
    horas_asignar: int
    estado: str

    class Config:
        from_attributes = True