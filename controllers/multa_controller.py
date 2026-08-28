from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.multa import Multa
from models.asistencia import Asistencia
from models.usuario import Usuario
from schemas.multa import RegistrarMultaInput, MultaResponse

def registrar_multa_controller(data: RegistrarMultaInput, db: Session) -> MultaResponse:
    #Verificar que el usuario existe
    usuario = db.query(Usuario).filter(
        Usuario.num_cuenta == data.num_cuenta
    ).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    #Verificar que el becario estaba inscrito en la actividad
    inscripcion = db.query(Asistencia).filter(
        Asistencia.actividad_id == data.actividad_id,
        Asistencia.num_cuenta == data.num_cuenta
    ).first()
    if not inscripcion:
        raise HTTPException(status_code=400, detail="El becario no estaba inscrito en esta actividad")

    #Verificar que el becario no asistió
    if inscripcion.check_in:
        raise HTTPException(status_code=400, detail="El becario sí asistió a la actividad")

    #Verificar que no tenga ya una multa por esta actividad
    multa_existente = db.query(Multa).filter(
        Multa.num_cuenta == data.num_cuenta,
        Multa.actividad_id == data.actividad_id
    ).first()
    if multa_existente:
        raise HTTPException(status_code=400, detail="Ya existe una multa para este becario en esta actividad")

    #Registrar multa
    nueva_multa = Multa(
        num_cuenta=data.num_cuenta,
        actividad_id=data.actividad_id,
        motivo=data.motivo,
        monto=data.monto
    )
    db.add(nueva_multa)
    db.commit()
    db.refresh(nueva_multa)

    return MultaResponse(
        id=nueva_multa.id,
        num_cuenta=nueva_multa.num_cuenta,
        actividad_id=nueva_multa.actividad_id,
        motivo=nueva_multa.motivo,
        monto=nueva_multa.monto,
        pagada=nueva_multa.pagada,
        fecha_multa=nueva_multa.fecha_multa
    )


def ver_multas_becario_controller(num_cuenta: str, db: Session):
    multas = db.query(Multa).filter(
        Multa.num_cuenta == num_cuenta
    ).all()

    return [
        MultaResponse(
            id=m.id,
            num_cuenta=m.num_cuenta,
            actividad_id=m.actividad_id,
            motivo=m.motivo,
            monto=m.monto,
            pagada=m.pagada,
            fecha_multa=m.fecha_multa
        )
        for m in multas
    ]


def ver_todas_multas_controller(db: Session):
    multas = db.query(Multa).all()

    return [
        MultaResponse(
            id=m.id,
            num_cuenta=m.num_cuenta,
            actividad_id=m.actividad_id,
            motivo=m.motivo,
            monto=m.monto,
            pagada=m.pagada,
            fecha_multa=m.fecha_multa
        )
        for m in multas
    ]