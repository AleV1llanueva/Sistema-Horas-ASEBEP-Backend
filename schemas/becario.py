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


class DatosPersonalesSinCorreo(BaseModel):
    num_cuenta: str
    p_nombre: str
    s_nombre: Optional[str] = None
    p_apellido: str
    s_apellido: Optional[str] = None
    correo_personal: Optional[str] = None
    correo_institucional: Optional[str] = None
    carrera: str
    telefono: Optional[str] = None

class DatosBecario(BaseModel):
    periodo_inicio: str
    anio_inicio: int
    # Mes de ingreso (1-12). Los registros antiguos pueden no tenerlo.
    mes_inicio: Optional[int] = None
    horas_totales: int
    horas_faltantes: int
    # Meses de aportación cubiertos antes del sistema (no son colones).
    monto_acumulado: int = 0
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

class BecarioGeneralSinCorreoResponse(BaseModel):
    credenciales: Credenciales
    datos_personales: DatosPersonalesSinCorreo
    datos_becario: DatosBecario


class BecariosPaginadosResponse(BaseModel):
    """
    Página de becarios junto con los totales necesarios
    para construir la navegación en el cliente.
    """
    elementos: list[BecarioGeneralResponse]
    total: int
    pagina: int
    limite: int
    total_paginas: int

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
    """
    Ajustes del perfil del becario.

    - horas_acumuladas: horas cubiertas por datos previos al sistema.
    - monto_acumulado: meses de aportación cubiertos por datos previos
      (el sistema no maneja colones en este campo).
    - anio_inicio / mes_inicio: mes desde el que se calculan las horas
      y aportaciones esperadas.
    """
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

    @field_validator("anio_inicio")
    @classmethod
    def validar_anio(cls, v):
        if v is not None and (v < 2000 or v > date.today().year):
            raise ValueError(
                f"El año de ingreso debe estar entre 2000 y {date.today().year}"
            )
        return v
