from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from utils.database import get_db
from schemas.becario import LoginResponse
from schemas.auth import LoginInput, TokenResponse
from schemas.pin_activacion import SolicitarPinInput, ActivarCuentaInput, MensajeResponse
from controllers.usuario import user_controller
from controllers.auth_controller import login_controller
from controllers.pin_controller import (
    solicitar_pin_controller, 
    activar_cuenta_controller,
    solicitar_pin_cambio_controller,
    cambiar_password_controller
)

from controllers.usuario import (
    user_controller
    )

router = APIRouter()

@router.get("/usuario/{num_cuenta}", response_model=LoginResponse, tags=["Becario"])
def login(num_cuenta: str, db: Session = Depends(get_db)):
    return user_controller(num_cuenta, db)


#Login
@router.post("/auth/login", response_model=TokenResponse, tags=["Autenticación"])
def login(data: LoginInput, db: Session = Depends(get_db)):
    return login_controller(data, db)

#Obtener PIN
@router.post("/auth/pin", response_model=MensajeResponse, tags=["Autenticación"])
async def solicitar_pin(data: SolicitarPinInput, db: Session = Depends(get_db)):
    return await solicitar_pin_controller(data, db)

#Activar cuenta
@router.post("/auth/activar", response_model=MensajeResponse, tags=["Autenticación"])
async def activar_cuenta(data: ActivarCuentaInput, db: Session = Depends(get_db)):
    return await activar_cuenta_controller(data, db)

#PIN cambiar contraseña
@router.post("/auth/password/pin", response_model=MensajeResponse, tags=["Autenticación"])
async def solicitar_pin_cambio(data: SolicitarPinInput, db: Session = Depends(get_db)):
    return await solicitar_pin_cambio_controller(data, db)

@router.post("/auth/password/nueva", response_model=MensajeResponse, tags=["Autenticación"])
async def cambiar_password(data: ActivarCuentaInput, db: Session = Depends(get_db)):
    return await cambiar_password_controller(data, db)