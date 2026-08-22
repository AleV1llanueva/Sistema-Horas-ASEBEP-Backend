import random 
import os
from datetime import datetime, timedelta, date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from utils.mail import enviar_pin

from models.usuario import Usuario 
from models.pin_activacion import PinActivacion
from models.pin_intentos import PinIntentos
from schemas.pin_activacion import SolicitarPinInput, ActivarCuentaInput
from core.security import hashear_password, verificar_password

LIMITE_PINES_POR_USUARIO = int(os.getenv("LIMITE_PINES_USUARIO", 2))

def _generar_pin() -> str:
    return str(random.randint(100000, 999999))


async def _solicitar_pin(usuario, db:Session, mensaje_exito:str):
    """
    Función privada para enviar PIN
    """
    #verificar límite de correos por usuario
    hoy = date.today()
    intento = db.query(PinIntentos).filter(
        PinIntentos.correo == usuario.correo_institucional,
        PinIntentos.fecha == hoy
    ).first()

    if intento and intento.intentos >= LIMITE_PINES_POR_USUARIO:
        raise HTTPException(status_code=429, detail="Límite de PINs diarios alcanzados, intenta mañana nuevamente")

    #Si existe un pin anterior eliminarlo
    db.query(PinActivacion).filter(
        PinActivacion.correo == usuario.correo_institucional
    ).delete()

    #Generar PIN y hashearlo
    pin = _generar_pin()
    pin_hash = hashear_password(pin)

    db.add(PinActivacion(
        correo = usuario.correo_institucional,
        pin_hash = pin_hash,
        expira_en = datetime.utcnow() + timedelta(minutes=15)
    ))

    #Actualizar los intentos del usuario 
    if intento:
        intento.intentos += 1
        es_ultimo = intento.intentos >= LIMITE_PINES_POR_USUARIO
    else:
        db.add(PinIntentos(correo=usuario.correo_institucional, fecha=hoy, intentos=1))
        es_ultimo = LIMITE_PINES_POR_USUARIO == 1

    db.commit()

    #Enviar Correo
    await enviar_pin(usuario.correo_institucional, pin, db)

    #Avisar si es el ultimo intento
    if es_ultimo:
        return {"mensaje": "PIN enviado. Este es tu último PIN disponible hoy, úsalo antes de que expire"}
    return {"mensaje": "Pin enviado a tu correo institucional"}


def _verificar_pin(usuario, pin: str, db: Session):
    # Buscar PIN por correo institucional del usuario
    pin_registro = (
        db.query(PinActivacion)
        .filter(PinActivacion.correo == usuario.correo_institucional)
        .first()
    )

    if not pin_registro:
        raise HTTPException(status_code=400, detail="PIN inválido")

    if datetime.utcnow() > pin_registro.expira_en:
        db.delete(pin_registro)
        db.commit()
        raise HTTPException(status_code=400, detail="PIN expirado, solicita uno nuevo")

    if not verificar_password(pin, pin_registro.pin_hash):
        raise HTTPException(status_code=400, detail="PIN inválido")

    db.delete(pin_registro)
    return pin_registro


async def solicitar_pin_controller(data: SolicitarPinInput, db:Session):
    #buscar usuario por numero de cuenta 
    usuario = db.query(Usuario).filter(
        Usuario.num_cuenta == data.num_cuenta
    ).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if usuario.active:
        raise HTTPException(status_code=400, detail= "Esta cuenta ya esta activada")

    return await _solicitar_pin(usuario, db, "PIN enviado a tu correo institucional")

async def solicitar_pin_cambio_controller(data: SolicitarPinInput, db:Session):
    # buscar usuario por numero de cuenta
    usuario = db.query(Usuario).filter(Usuario.num_cuenta == data.num_cuenta).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not usuario.active:
        raise HTTPException(status_code=400, detail="Esta cuenta no esta activada")

    return await _solicitar_pin(usuario, db, "PIN enviado a tu correo institucional")


async def activar_cuenta_controller(data: ActivarCuentaInput, db: Session):
    # Buscar usuario por num_cuenta
    usuario = db.query(Usuario).filter(Usuario.num_cuenta == data.num_cuenta).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    _verificar_pin(usuario, data.pin, db)

    # Activar cuenta
    usuario.password_hash = hashear_password(data.nueva_password)
    usuario.active = True
    db.commit()
    return {"mensaje": "Cuenta activada exitosamente, ya puedes iniciar sesión"}

async def cambiar_password_controller(data: ActivarCuentaInput, db: Session):
    usuario = db.query(Usuario).filter(Usuario.num_cuenta == data.num_cuenta).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not usuario.active:
        raise HTTPException(status_code=400, detail="Cuenta no activada")

    _verificar_pin(usuario, data.pin, db)
    usuario.password_hash = hashear_password(data.nueva_password)
    db.commit()

    return {"mensaje": "Contraseña cambiada exitosamente"}
