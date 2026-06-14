# controllers/auth_controller.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.usuario import Usuario
from schemas.auth import LoginInput, TokenResponse
from core.security import verificar_dominio, verificar_password, crear_token

def login_controller(data: LoginInput, db: Session) -> TokenResponse:
    # 1. Validar dominio institucional
    if not verificar_dominio(data.correo):
        raise HTTPException(
            status_code=400,
            detail="Debe usar su correo institucional"
        )

    # 2. Buscar usuario por correo institucional
    usuario = db.query(Usuario).filter(
        Usuario.correo_institucional == data.correo).first()

    # 3. Verificar que existe y que la contraseña es correcta
    # — mismo mensaje para ambos casos, por seguridad
    if not usuario or not verificar_password(data.password, usuario.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas"
        )

    # 4. Verificar que el usuario está activo \
    if not usuario.active:
        raise HTTPException(
            status_code=401,
            detail="Usuario inactivo, contacte al administrador"
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