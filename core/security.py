import os 
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
from fastapi import HTTPException
from jose import jwt, JWTError

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRES_HOURS = 1
DOMINIO_PERMITIDO = os.getenv("DOMINIO_CORREO", "unah.edu.hn")


## CONTRASEÑAS

def hashear_password(password: str) -> str:
    """
    Usar bcrypt para nunca guardar la contraseña real en la BD
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verificar_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

## JWT

def crear_token(correo: str, rol: str) -> str: 
    payload = {
        "correo": correo,
        "rol": rol,
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRES_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decodificar_token(token:str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithm=ALGORITHM)
    except:
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
            
            request.state.correo = payload.get("sub")
            request.state.rol = payload.get("rol")

            return await func(*args, **kwargs)
        return wrapper 
    return decorator


def becario(func):
    return require_rol("becario")(func)

def solo_admin_horas(func):
    return require_rol("admin_horas", "admin_general")(func)

def solo_admin_aportaciones(func):
    return require_rol("admin_aportaciones", "admin_general")(func)

def solo_admin_general(func):
    return require_rol("admin_general")(func)

def cualquier_usuario(func):
    return require_rol("becario", "admin_horas", "admin_aportaciones", "admin_general")(func)
