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

    @field_validator("hora_inicio", "hora_final", mode="before")
    @classmethod
    def validar_hora_formato(cls, v):
        if isinstance(v, str):
            partes = v.split(":")
            if len(partes) >= 2:
                hora = partes[0].zfill(2)
                minutos = partes[1].zfill(2)
                segundos = partes[2].zfill(2) if len(partes) > 2 else "00"
                return f"{hora}:{minutos}:{segundos}"
        return v

    @field_validator("hora_inicio")
    @classmethod
    def validar_hora_inicio(cls, v, info):
        fecha = info.data.get("fecha_actividad")
        if fecha:
            from datetime import datetime, timezone
            ahora = datetime.now(timezone.utc).replace(tzinfo=None)
            # quitar timezone del time si lo tiene
            v_sin_tz = v.replace(tzinfo=None) if hasattr(v, 'tzinfo') and v.tzinfo else v
            inicio = datetime.combine(fecha, v_sin_tz)
            if inicio <= ahora:
                raise ValueError("El horario de la actividad ya pasó")
        return v

    @field_validator("hora_final")
    @classmethod
    def validar_hora_final(cls, v, info):
        hora_inicio = info.data.get("hora_inicio")
        if hora_inicio and v <= hora_inicio:
            raise ValueError("La hora final debe ser mayor a la hora inicial")
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