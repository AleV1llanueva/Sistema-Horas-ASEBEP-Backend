from pydantic import BaseModel, field_validator

class LoginInput(BaseModel):
    """
    Vallida la información que se manda al frontend
    """
    correo: str
    password: str

    @field_validator("correo")
    @classmethod
    def correo_no_vacio(cls, v):
        if not v or not v.strip():
            raise ValueError("El correo no puede estar vacío")
        
        return v.lower().strip()
    
    @field_validator("password")
    @classmethod
    def password_no_vacio(cls, v):
        if not v or not v.strip():
            raise ValueError("la contraseña no puede estar vacía")
        return v
    
class TokenResponse(BaseModel):
    """
    El retorno que dará la API 
    """
    access_token: str
    token_type: str = "bearer"
    rol: str