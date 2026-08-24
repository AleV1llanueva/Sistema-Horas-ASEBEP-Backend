# controllers/actividad_controller.py
from datetime import date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.actividad import Actividad
from models.estado_actividad import EstadoActividad
from models.asistencia import Asistencia
from schemas.actividad import CrearActividadInput, ActividadResponse

def _cupos_disponibles(actividad_id:int, cupos_totales:int, db:Session) -> int:
    inscritos = db.query(Asistencia).filter(
        Asistencia.actividad_id == actividad_id
    ).count()
    return cupos_totales - inscritos

def crear_actividad_controller(data: CrearActividadInput, db: Session) -> ActividadResponse:
    #Obtener estado "programada" por defecto
    estado = db.query(EstadoActividad).filter(
        EstadoActividad.nombre_estado == "Programada"
    ).first()

    if not estado:
        raise HTTPException(status_code=500, detail="Estado 'Programada' no encontrado en BD")

    #Crear actividad
    nueva_actividad = Actividad(
        titulo=data.titulo,
        descripcion=data.descripcion,
        ubicacion=data.ubicacion,
        fecha_actividad=data.fecha_actividad,
        horas_asignar=data.horas_asignar,
        hora_inicio=data.hora_inicio,
        hora_final=data.hora_final,
        cupos=data.cupos,
        estado_actividad_id=estado.id
    )

    db.add(nueva_actividad)
    db.commit()
    db.refresh(nueva_actividad)

    return ActividadResponse(
        id=nueva_actividad.id,
        titulo=nueva_actividad.titulo,
        descripcion=nueva_actividad.descripcion,
        ubicacion=nueva_actividad.ubicacion,
        fecha_actividad=nueva_actividad.fecha_actividad,
        horas_asignar=nueva_actividad.horas_asignar,
        hora_inicio=nueva_actividad.hora_inicio,
        hora_final=nueva_actividad.hora_final,
        cupos=nueva_actividad.cupos,
        cupos_disponibles=_cupos_disponibles(nueva_actividad.id, nueva_actividad.cupos, db),
        estado=estado.nombre_estado
    )


def ver_actividades_controller(db: Session):
    hoy = date.today()

    actividades = db.query(Actividad).join(EstadoActividad).filter(
        Actividad.fecha_actividad >= hoy,
        EstadoActividad.nombre_estado == "Programada"
    ).all()

    return [
        ActividadResponse(
            id=a.id,
            titulo=a.titulo,
            descripcion=a.descripcion,
            ubicacion=a.ubicacion,
            fecha_actividad=a.fecha_actividad,
            horas_asignar=a.horas_asignar,
            hora_inicio=a.hora_inicio,
            hora_final=a.hora_final,
            cupos=a.cupos,
            cupos_disponibles=_cupos_disponibles(a.id, a.cupos, db),
            estado=a.estado.nombre_estado
        )
        for a in actividades
    ]