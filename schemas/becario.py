from pydantic import BaseModel
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
    correo_personal: str
    correo_inst: str
    carrera: str
    # anio_nacimiento: int
    telefono: Optional[str] = None

class DatosBecario(BaseModel):
    periodo_inicio: str
    anio_inicio: int
    horas_acumuladas: int
    horas_faltantes: int
    meses_sin_pagar: int
    estado_beca: str

class LoginResponse(BaseModel):
    credenciales: Credenciales
    datos_personales: DatosPersonales
    datos_becario: DatosBecario