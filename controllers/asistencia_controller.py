from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.asistencia import Asistencia
from models.actividad import Actividad
from models.estado_asistencia import EstadoAsistencia
from models.estado_actividad import EstadoActividad
from schemas.asistencia import InscripcionInput, InscripcionResponse, MisInscripcionesResponse

def inscribirse_controller(data: InscripcionInput, num_cuenta: str, db: Session):
    # 1. Verificar que la actividad existe
    actividad = db.query(Actividad).filter(Actividad.id == data.actividad_id).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    # 2. Verificar que la actividad está programada
    estado_actividad = db.query(EstadoActividad).filter(
        EstadoActividad.id == actividad.estado_actividad_id
    ).first()
    if estado_actividad.nombre_estado != "programada":
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
        EstadoAsistencia.nombre_estado == "inscrito"
    ).first()

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
