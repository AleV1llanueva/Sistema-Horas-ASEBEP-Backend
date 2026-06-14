import random 
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.usuario import Usuario 
from models.pin_activacion import PinActivacion
from schemas.pin_activacion import SolicitarPinInput, ActivarCuentaInput
from core.security import hashear_password, verificar_password


def _generar_pin() -> str:
    return str(random.randint(100000, 999999))


async def solicitar_pin_controller(data: SolicitarPinInput, db:Session):
    usuario = db.query(Usuario).filter(
        Usuario.correo_institucional == data.correo
    ).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if usuario.active:
        raise HTTPException(status_code=400, detail= "Esta cuenta ya esta activada")
    
    #SI existe un pin anterior eliminarlo 
    db.query(PinActivacion).filter(
        PinActivacion.correo == data.correo
    ).delete()

    pin = _generar_pin()
    pin_hash = hashear_password(pin)

    nuevo_pin = PinActivacion(
        correo=data.correo,
        pin_hash=pin_hash,
        expira_en = datetime.utcnow() + timedelta(minutes=15)
    )

    db.add(nuevo_pin)
    db.commit()

    from utils.mail import enviar_pin
    await enviar_pin(data.correo, pin)

    return {"mensaje": "Pin enviado a tu correo institucional"}


async def activar_cuenta_controller(data: ActivarCuentaInput, db: Session):

    pin_registro = db.query(PinActivacion).filter(
        PinActivacion.correo == data.correo
    ).first()
    
    if not pin_registro:
        raise HTTPException(status_code=400, detail="Pin invalido")
    
    if datetime.utcnow() > pin_registro.expira_en:
        db.delete(pin_registro)
        db.commit()
        raise HTTPException(status_code=400, detail="PIN expirado, solicita uno nuevo")
    
    if not verificar_password(data.pin, pin_registro.pin_hash):
        raise HTTPException(status_code=400, detail="PIN inválido")
    
    usuario = db.query(Usuario).filter(
        Usuario.correo_institucional == data.correo
    ).first()

    usuario.password_hash = hashear_password(data.nueva_password)
    usuario.active = True

    db.delete(pin_registro)
    db.commit()

    return {"mensaje": "Cuenta activada eistosamente, ya puedes iniciar sesión"}
