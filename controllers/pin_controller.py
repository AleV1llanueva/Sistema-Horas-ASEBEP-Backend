import random 
import os
from datetime import datetime, timedelta, date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.usuario import Usuario 
from models.pin_activacion import PinActivacion
from models.pin_intentos import PinIntentos
from schemas.pin_activacion import SolicitarPinInput, ActivarCuentaInput
from core.security import hashear_password, verificar_password

LIMITE_PINES_POR_USUARIO = int(os.getenv("LIMITE_PINES_USUARIO", 2))

def _generar_pin() -> str:
    return str(random.randint(100000, 999999))


async def solicitar_pin_controller(data: SolicitarPinInput, db:Session):
    #buscar usuario por numero de cuenta 
    usuario = db.query(Usuario).filter(
        Usuario.num_cuenta == data.num_cuenta
    ).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if usuario.active:
        raise HTTPException(status_code=400, detail= "Esta cuenta ya esta activada")

    #verificar limite de correos por usuario 
    hoy = date.today()
    intento = db.query(PinIntentos).filter(
        PinIntentos.correo == usuario.correo_institucional,
        PinIntentos.fecha == hoy
    ).first()

    if intento and intento.intentos >= LIMITE_PINES_POR_USUARIO:
        raise HTTPException(
            status_code=429,
            detail="Límite de PINs diarios alcanzado, intenta mañana"
        )

    
    #SI existe un pin anterior eliminarlo 
    db.query(PinActivacion).filter(
        PinActivacion.correo == usuario.correo_institucional
    ).delete()

    #Generar PIN y Hashearlo
    pin = _generar_pin()
    pin_hash = hashear_password(pin)

    nuevo_pin = PinActivacion(
        correo=usuario.correo_institucional,
        pin_hash=pin_hash,
        expira_en = datetime.utcnow() + timedelta(minutes=15)
    )

    db.add(nuevo_pin)

    #Actualizar los intentos del usuario
    if intento:
        intento.intentos += 1
        es_ultimo = intento.intentos >= LIMITE_PINES_POR_USUARIO
    else:
        db.add(PinIntentos(correo=usuario.correo_institucional, fecha=hoy, intentos=1))
        es_ultimo = LIMITE_PINES_POR_USUARIO == 1

    db.commit()

    #Enviar correo
    from utils.mail import enviar_pin
    await enviar_pin(usuario.correo_institucional, pin, db)

    #Avisar si es ultimo correo: 
    if es_ultimo:
        return {"mensaje": "PIN enviado. Este es tu último PIN disponible hoy, úsalo antes de que expire"}

    return {"mensaje": "Pin enviado a tu correo institucional"}


async def activar_cuenta_controller(data: ActivarCuentaInput, db: Session):
    #Buscar usuario por num_cuenta
    usuario = db.query(Usuario).filter(
        Usuario.num_cuenta == data.num_cuenta
    ).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    #Buscar PIN por correo institucional del usuario
    pin_registro = db.query(PinActivacion).filter(
        PinActivacion.correo == usuario.correo_institucional
    ).first()

    if not pin_registro:
        raise HTTPException(status_code=400, detail="PIN inválido")

    if datetime.utcnow() > pin_registro.expira_en:
        db.delete(pin_registro)
        db.commit()
        raise HTTPException(status_code=400, detail="PIN expirado, solicita uno nuevo")

    if not verificar_password(data.pin, pin_registro.pin_hash):
        raise HTTPException(status_code=400, detail="PIN inválido")

    #Activar cuenta
    usuario.password_hash = hashear_password(data.nueva_password)
    usuario.active = True

    db.delete(pin_registro)
    db.commit()

    return {"mensaje": "Cuenta activada exitosamente, ya puedes iniciar sesión"}