from pydantic import BaseModel, field_validator

class LoginInput(BaseModel):
    """
    Vallida la información que se manda al frontend
    """
    num_cuenta: str
    password: str

    @field_validator("num_cuenta")
    @classmethod
    def num_cuenta_no_vacio(cls, v):
        if not v or not v.strip():
            raise ValueError("El número de cuenta no puede estar vacío")
        
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