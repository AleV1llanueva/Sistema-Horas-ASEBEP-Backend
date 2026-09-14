from pydantic import BaseModel, field_validator
from typing import Optional


class CarreraInput(BaseModel):
    nombre_carrera: str

    @field_validator("nombre_carrera")
    @classmethod
    def validar_nombre_carrera(cls, v):
        if not v or not v.strip():
            raise ValueError("El nombre de la carrera no puede estar vacío")
        return v.strip()



class CarreraResponse(BaseModel):
    id: int
    nombre_carrera: str
    activo: bool

    class Config:
        from_attributes = True