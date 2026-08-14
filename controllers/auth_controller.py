# controllers/auth_controller.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.usuario import Usuario
from schemas.auth import LoginInput, TokenResponse
from core.security import verificar_password, crear_token

def login_controller(data: LoginInput, db: Session) -> TokenResponse:
    #Buscar usuario por numero de cuenta
    usuario = db.query(Usuario).filter(
        Usuario.num_cuenta == data.num_cuenta
        ).first()
    
    if not usuario:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    # Verificar que está activo antes de la contraseña
    if not usuario.active:
        raise HTTPException(
            status_code=401,
            detail="Usuario inactivo, solicita tu PIN"
        )

    # Verificar que existe y que la contraseña es correcta
    if not verificar_password(data.password, usuario.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas"
        )

    # 5. Obtener nombre del rol
    rol = usuario.rol.nombre_rol if usuario.rol else None
    if not rol:
        raise HTTPException(
            status_code=500,
            detail="El usuario no tiene un rol asignado"
        )

    # 6. Emitir token
    token = crear_token(correo=usuario.correo_institucional, rol=rol)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        rol=rol
    )