from pydantic import BaseModel
from pydantic import BaseModel, field_validator

class SolicitarPinInput(BaseModel):
    correo: str

class ActivarCuentaInput(BaseModel):
    correo: str
    pin: str
    nueva_password: str

    @field_validator("nueva_password")
    @classmethod
    def validar_password(cls, v):
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe tener al menos una mayúscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe tener al menos un número")
        return v

class MensajeResponse(BaseModel):
    mensaje: str