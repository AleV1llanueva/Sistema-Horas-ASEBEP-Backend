import os 
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
from fastapi import HTTPException
from jose import jwt, JWTError
from enum import Enum

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRES_HOURS = 1
DOMINIO_PERMITIDO = os.getenv("DOMINIO_CORREO", "unah.hn")

class RolEnum(str, Enum):
    BECARIO = "Becario"
    ADMIN_GENERAL = "Admin General" 
    ADMIN_APORTACIONES = "Admin Aportaciones"
    ADMIN_HORAS = "Admin Horas"

## CONTRASEÑAS

def hashear_password(password: str) -> str:
    """
    Usar bcrypt para nunca guardar la contraseña real en la BD
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verificar_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

## JWT

def crear_token(correo: str, rol: str, num_cuenta: str) -> str: 
    payload = {
        "correo": correo,
        "rol": rol,
        "num_cuenta": num_cuenta,
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRES_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decodificar_token(token:str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception as e:
        print(f"Error decodificando token: {e}")
        raise HTTPException(status_code=401, detail= "Token inválido o expirado")
    
## VALIDACIONES 

def verificar_dominio(correo: str) -> bool:
    return correo.endswith(f"@{DOMINIO_PERMITIDO}")

def extraer_payload(request) -> dict:
    authorization: str = request.headers.get("Authorization", "")
    partes = authorization.split()

    if len(partes) != 2 or partes[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Header de autorización inválido")
    
    return decodificar_token(partes[1])


## DECORADORES

def require_rol(*roles_permitidos):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                raise HTTPException(status_code=400, detail="Request no encontrado")
            
            payload = extraer_payload(request)

            if payload.get("rol") not in roles_permitidos:
                raise HTTPException(status_code=403, detail="Sin permisos suficientes")
            
            request.state.correo = payload.get("correo")
            request.state.rol = payload.get("rol")
            request.state.num_cuenta = payload.get("num_cuenta")

            return await func(*args, **kwargs)
        return wrapper 
    return decorator


def becario(func):
    return require_rol(RolEnum.BECARIO)(func)

def admin_horas(func):
    return require_rol(RolEnum.ADMIN_HORAS, RolEnum.ADMIN_GENERAL)(func)

def admin_aportaciones(func):
    return require_rol(RolEnum.ADMIN_APORTACIONES, RolEnum.ADMIN_GENERAL)(func)

def admin_general(func):
    return require_rol(RolEnum.ADMIN_GENERAL)(func)

def cualquier_usuario(func):
    return require_rol(
        RolEnum.BECARIO, 
        RolEnum.ADMIN_HORAS, 
        RolEnum.ADMIN_APORTACIONES, 
        RolEnum.ADMIN_GENERAL
    )(func)

def solo_administradores(func):
    return require_rol(
        RolEnum.ADMIN_HORAS, 
        RolEnum.ADMIN_APORTACIONES, 
        RolEnum.ADMIN_GENERAL
    )(func)
