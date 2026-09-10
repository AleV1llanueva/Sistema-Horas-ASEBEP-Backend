from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AportacionResponse(BaseModel):
    id: int
    num_cuenta: str
    num_referencia: str
    descripcion: Optional[str]
    ruta_pdf: str
    estado: str
    meses_aprobados: int = 0
    fecha_subida: datetime

    class Config:
        from_attributes = True

class RevisionAportacionInput(BaseModel):
    estado: str
    meses_aprobados: int = 0

class AportacionCrear(BaseModel):
    num_referencia: str
    descripcion:str