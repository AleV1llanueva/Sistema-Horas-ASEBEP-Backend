import os
from jose import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.asistencia import Asistencia
from models.actividad import Actividad
from models.estado_asistencia import EstadoAsistencia
from models.estado_actividad import EstadoActividad
from schemas.asistencia import InscripcionInput, InscripcionResponse, MisInscripcionesResponse
from utils.qr import generar_qr

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
QR_TTL_MIN = 10

def inscribirse_controller(data: InscripcionInput, num_cuenta: str, db: Session):
    # 1. Verificar que la actividad existe
    actividad = db.query(Actividad).filter(Actividad.id == data.actividad_id).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    # 2. Verificar que la actividad está programada
    estado_actividad = db.query(EstadoActividad).filter(
        EstadoActividad.id == actividad.estado_actividad_id
    ).first()
    if estado_actividad.nombre_estado != "Programada":
        raise HTTPException(status_code=400, detail="La actividad no está disponible para inscripción")

    # 3. Verificar que la actividad no haya pasado
    if actividad.fecha_actividad < datetime.utcnow().date():
        raise HTTPException(status_code=400, detail="La actividad ya pasó")

    # 4. Verificar que haya cupos disponibles
    inscritos = db.query(Asistencia).filter(
        Asistencia.actividad_id == data.actividad_id
    ).count()
    if inscritos >= actividad.cupos:
        raise HTTPException(status_code=400, detail="No hay cupos disponibles")

    # 5. Verificar que no esté ya inscrito
    ya_inscrito = db.query(Asistencia).filter(
        Asistencia.actividad_id == data.actividad_id,
        Asistencia.num_cuenta == num_cuenta
    ).first()
    if ya_inscrito:
        raise HTTPException(status_code=400, detail="Ya estás inscrito en esta actividad")

    # 6. Obtener estado "inscrito"
    estado = db.query(EstadoAsistencia).filter(
        EstadoAsistencia.nombre_estado == "Inscrito"
    ).first()

    if not estado:
        raise HTTPException(status_code=500, detail="El estado 'Inscrito' no está configurado en la base de datos")

    # 7. Crear inscripción
    nueva_inscripcion = Asistencia(
        actividad_id=data.actividad_id,
        num_cuenta=num_cuenta,
        check_in=False,
        check_out=False,
        estado_asistencia_id=estado.id,
        horas_registradas=0
    )

    db.add(nueva_inscripcion)
    db.commit()
    db.refresh(nueva_inscripcion)

    return InscripcionResponse(
        id=nueva_inscripcion.id,
        actividad_id=nueva_inscripcion.actividad_id,
        num_cuenta=nueva_inscripcion.num_cuenta,
        estado=estado.nombre_estado
    )


def cancelar_inscripcion_controller(actividad_id: int, num_cuenta: str, db: Session):
    # 1. Buscar inscripción
    inscripcion = db.query(Asistencia).filter(
        Asistencia.actividad_id == actividad_id,
        Asistencia.num_cuenta == num_cuenta
    ).first()

    if not inscripcion:
        raise HTTPException(status_code=404, detail="No estás inscrito en esta actividad")

    # 2. Verificar que la actividad no haya comenzado
    actividad = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    ahora = datetime.utcnow()
    inicio_actividad = datetime.combine(actividad.fecha_actividad, actividad.hora_inicio)

    if ahora >= inicio_actividad - timedelta(hours=2):
        raise HTTPException(
            status_code=400,
            detail="No puedes cancelar con menos de 2 horas de anticipación"
        )

    # 3. Eliminar inscripción
    db.delete(inscripcion)
    db.commit()

    return {"mensaje": "Inscripción cancelada exitosamente"}


def mis_inscripciones_controller(num_cuenta: str, db: Session):
    inscripciones = db.query(Asistencia).filter(
        Asistencia.num_cuenta == num_cuenta
    ).all()

    return [
        MisInscripcionesResponse(
            id=i.id,
            actividad_id=i.actividad_id,
            titulo=i.actividad.titulo if i.actividad else None,
            fecha_actividad=i.actividad.fecha_actividad,
            hora_inicio=i.actividad.hora_inicio,
            hora_final=i.actividad.hora_final,
            ubicacion=i.actividad.ubicacion,
            horas_asignar=i.actividad.horas_asignar,
            estado=i.estado.nombre_estado
        )
        for i in inscripciones
    ]

def _verificar_inscripcion(actividad_id: int, num_cuenta: str, db: Session) -> tuple:
    """Retorna (actividad, inscripcion) o lanza HTTPException"""
    actividad = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    inscripcion = db.query(Asistencia).filter(
        Asistencia.actividad_id == actividad_id,
        Asistencia.num_cuenta == num_cuenta
    ).first()
    if not inscripcion:
        raise HTTPException(status_code=403, detail="No estás inscrito en esta actividad")

    return actividad, inscripcion

def _verificar_token_qr(token: str, tipo: str, db) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        raise HTTPException(status_code=400, detail="QR inválido o expirado")

    if payload.get("tipo") != tipo:
        raise HTTPException(status_code=400, detail="QR incorrecto")

    actividad_id = payload.get("actividad_id")
    actividad = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    token_guardado = actividad.token_entrada if tipo == "entrada" else actividad.token_salida

    if not actividad or token_guardado != token:
        raise HTTPException(status_code=400, detail="QR inválido")

    return payload

def _actualizar_estado(inscripcion, nombre_estado: str, db):
    estado = db.query(EstadoAsistencia).filter(
        EstadoAsistencia.nombre_estado == nombre_estado
    ).first()
    if estado:
        inscripcion.estado_asistencia_id = estado.id


def _sumar_horas(inscripcion, actividad, num_cuenta: str, db):
    from models.becario import Becario
    inscripcion.check_out = True
    inscripcion.horas_registradas = actividad.horas_asignar
    perfil = db.query(Becario).filter(Becario.num_cuenta == num_cuenta).first()
    if perfil:
        perfil.horas_acumuladas += actividad.horas_asignar

def generar_qr_entrada_controller(actividad_id: int, db) -> bytes:
    #buscar actividad
    actividad = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    #generar token JWT para el QR
    token = jwt.encode(
        {
            "actividad_id": actividad_id,
            "tipo": "entrada",
            "exp": datetime.utcnow() + timedelta(minutes=QR_TTL_MIN)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    #Guardar token en la actividad
    actividad.token_entrada = token
    db.commit()

    return generar_qr(token, "entrada")

def registrar_entrada_qr_controller(token: str, num_cuenta:str, db):
    payload = _verificar_token_qr(token, "entrada", db)
    actividad, inscripcion = _verificar_inscripcion(payload["actividad_id"], num_cuenta, db)

    #Verificar que no haya registrado entrada ya 
    if inscripcion.check_in:
        raise HTTPException(status_code=400, detail="Ya registraste tu entrada")

    inscripcion.check_in = True
    _actualizar_estado(inscripcion, "Asistio", db)
    db.commit()
    return {"mensaje": "Entrada registrada exitosamente"}

def generar_qr_salida_controller(actividad_id: int, db) -> bytes:
    #buscar actividad
    actividad = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    #generar token JWT para el QR
    token = jwt.encode(
        {
            "actividad_id": actividad_id,
            "tipo": "salida",
            "exp": datetime.utcnow() + timedelta(minutes=QR_TTL_MIN)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    #Guardar token en la actividad
    actividad.token_salida = token
    db.commit()

    return generar_qr(token, "salida")

def registrar_salida_qr_controller(token:str, num_cuenta: str, db):
    payload = _verificar_token_qr(token, "salida", db)
    actividad, inscripcion = _verificar_inscripcion(payload["actividad_id"], num_cuenta, db)

    if not inscripcion.check_in:
        raise HTTPException(status_code=400, detail="Debes registrar entrada primero")
    if inscripcion.check_out:
        raise HTTPException(status_code=400, detail="Ya registraste tu sallida")

    _sumar_horas(inscripcion, actividad, num_cuenta, db)
    db.commit()
    return {"mensaje": "Salida registrada, horas acumuladas"}

def registrar_entrada_manual_controller(actividad_id: int, num_cuenta: str, db: Session):
    actividad, inscripcion = _verificar_inscripcion(actividad_id, num_cuenta, db)

    if inscripcion.check_in:
        raise HTTPException(status_code=400, detail="Ya se registró la entrada")

    inscripcion.check_in = True
    _actualizar_estado(inscripcion, "Asistió", db)
    db.commit()
    return {"mensaje": f"Entrada registrada para {num_cuenta}"}


def registrar_salida_manual_controller(actividad_id: int, num_cuenta: str, db: Session):
    actividad, inscripcion = _verificar_inscripcion(actividad_id, num_cuenta, db)

    if not inscripcion.check_in:
        raise HTTPException(status_code=400, detail="Debes registrar entrada primero")
    if inscripcion.check_out:
        raise HTTPException(status_code=400, detail="Ya se registró la salida")

    _sumar_horas(inscripcion, actividad, num_cuenta, db)
    db.commit()
    return {"mensaje": f"Salida registrada para {num_cuenta}"}

def ver_lista_asistencia_controller(actividad_id: int, db):
    actividad = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    inscripciones = db.query(Asistencia).filter(
        Asistencia.actividad_id == actividad_id
    ).all()

    return [
        {
            "num_cuenta": i.num_cuenta,
            "check_in": i.check_in,
            "check_out": i.check_out,
            "horas_registradas": i.horas_registradas,
            "estado": i.estado.nombre_estado
        }
        for i in inscripciones
    ]

