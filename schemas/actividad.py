# schemas/actividad.py
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, time

class CrearActividadInput(BaseModel):
    titulo: str
    descripcion: str
    ubicacion: str
    fecha_actividad: date
    horas_asignar: int
    hora_inicio: time
    hora_final: time
    cupos: int

    @field_validator("titulo", "descripcion", "ubicacion")
    @classmethod
    def validar_no_vacio(cls, v):
        if not v or not v.strip():
            raise ValueError("Este campo no puede estar vacío")
        return v.strip()

    @field_validator("horas_asignar")
    @classmethod
    def validar_horas(cls, v):
        if v <= 0:
            raise ValueError("Las horas deben ser mayor a 0")
        return v

    @field_validator("cupos")
    @classmethod
    def validar_cupos(cls, v):
        if v <= 0:
            raise ValueError("Los cupos deben ser mayor a 0")
        return v

    @field_validator("fecha_actividad")
    @classmethod
    def validar_fecha(cls, v):
        print(f"Fecha recibida: {v} | Hoy: {date.today()}")
        if v < date.today():
            raise ValueError("La fecha de la actividad no puede ser en el pasado")
        return v

    @field_validator("hora_inicio")
    @classmethod
    def validar_hora(cls, v, info):
        fecha = info.data.get("fecha_actividad")
        if fecha:
            from datetime import datetime
            ahora = datetime.now()
            inicio = datetime.combine(fecha, v)
            if inicio <= ahora:
                raise ValueError("El horario de la actividad ya pasó")
        return v


class ActividadResponse(BaseModel):
    id: int
    titulo: str
    descripcion: str
    ubicacion: str
    fecha_actividad: date
    horas_asignar: int
    hora_inicio: time
    hora_final: time
    cupos: int
    cupos_disponibles: int
    estado: str

    class Config:
        from_attributes = True