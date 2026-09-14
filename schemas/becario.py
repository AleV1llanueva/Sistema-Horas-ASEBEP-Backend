from pydantic import BaseModel, field_validator
from datetime import date
from typing import Optional

class Credenciales(BaseModel):
    rol: str
    active: bool

class DatosPersonales(BaseModel):
    num_cuenta: str
    p_nombre: str
    s_nombre: Optional[str] = None
    p_apellido: str
    s_apellido: Optional[str] = None
    correo_personal: Optional[str] = None
    correo_institucional: str
    carrera: str
    telefono: Optional[str] = None

class DatosBecario(BaseModel):
    periodo_inicio: str
    anio_inicio: int
    horas_totales: int
    horas_faltantes: int
    meses_sin_pagar: int
    estado_beca: str


class LoginResponse(BaseModel):
    credenciales: Credenciales
    datos_personales: DatosPersonales
    datos_becario: DatosBecario

class PerfilBecarioResponse(BaseModel):
    periodo_inicio: str
    anio_inicio: int
    mes_inicio: int
    horas_acumuladas: int
    monto_acumulado: int

class BecarioGeneralResponse(BaseModel):
    credenciales: Credenciales
    datos_personales: DatosPersonales
    datos_becario: DatosBecario

class AdminInfoResponse(BaseModel):
    num_cuenta: str
    primer_nombre: str
    segundo_nombre: str | None
    primer_apellido: str
    segundo_apellido: str | None
    correo_institucional: str
    rol: str

    class Config:
        from_attributes = True

class BecarioUpdateInput(BaseModel):
    anio_inicio: Optional[int] = None
    mes_inicio: Optional[int] = None
    horas_acumuladas: Optional[int] = None
    estado_beca_id: Optional[int] = None
    fecha_fin_beca: Optional[date] = None
    monto_acumulado: Optional[int] = None

    @field_validator("horas_acumuladas", "monto_acumulado")
    @classmethod
    def validar_no_negativos(cls, v):
        if v is not None and v < 0:
            raise ValueError("El valor no puede ser negativo")
        return v

    @field_validator("mes_inicio")
    @classmethod
    def validar_mes(cls, v):
        if v is not None and (v < 1 or v > 12):
            raise ValueError("El mes debe estar entre 1 y 12")
        return v