# controllers/auth_controller.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.usuario import Usuario
from models.becario import Becario

from controllers.becario_controller import verificar_y_finalizar_por_fecha
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

    # Obtener nombre del rol
    rol = usuario.rol.nombre_rol if usuario.rol else None
    if not rol:
        raise HTTPException(
            status_code=500,
            detail="El usuario no tiene un rol asignado"
        )

    if rol == "Becario":
        becario = db.query(Becario).filter(Becario.num_cuenta == usuario.num_cuenta).first()
        if becario:
            verificar_y_finalizar_por_fecha(becario, db)
            estado_nombre = becario.estado.nombre_estado if becario.estado else None
            if estado_nombre != "Activo":
                raise HTTPException(
                    status_code=403,
                    detail=f"Tu perfil de becario está en estado '{estado_nombre}'. Contacta al administrador"
                )

    # 6. Emitir token
    token = crear_token(correo=usuario.correo_institucional, rol=rol, num_cuenta=usuario.num_cuenta)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        rol=rol
    )