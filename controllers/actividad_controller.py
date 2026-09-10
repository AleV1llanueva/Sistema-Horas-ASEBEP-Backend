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

from datetime import datetime

def _calcular_estado_dinamico(actividad) -> str:
    ahora = datetime.now()
    
    # Combinar fecha y hora de la actividad para crear objetos datetime exactos
    inicio_dt = datetime.combine(actividad.fecha_actividad, actividad.hora_inicio)
    fin_dt = datetime.combine(actividad.fecha_actividad, actividad.hora_final)
    
    if ahora < inicio_dt:
        return "Programada"
    elif inicio_dt <= ahora <= fin_dt:
        return "En curso"
    else:
        return "Completada"


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
            estado=_calcular_estado_dinamico(a)
        )
        for a in actividades
    ]

def editar_actividad_controller(actividad_id: int, data: CrearActividadInput, db: Session) -> ActividadResponse:
    # 1. Buscar la actividad existente
    actividad = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    # 2. Validar que la actividad aún no haya pasado (que sea en el futuro o hoy)
    # Comparamos con la fecha actual
    hoy = date.today()
    if actividad.fecha_actividad < hoy:
        raise HTTPException(
            status_code=400, 
            detail="No se puede editar una actividad cuya fecha ya pasó"
        )

    # 3. Actualizar los campos con los nuevos datos enviados
    actividad.titulo = data.titulo
    actividad.descripcion = data.descripcion
    actividad.ubicacion = data.ubicacion
    actividad.fecha_actividad = data.fecha_actividad
    actividad.horas_asignar = data.horas_asignar
    actividad.hora_inicio = data.hora_inicio
    actividad.hora_final = data.hora_final
    actividad.cupos = data.cupos

    db.commit()
    db.refresh(actividad)

    # 4. Retornar la respuesta formateada igual que en la creación
    return ActividadResponse(
        id=actividad.id,
        titulo=actividad.titulo,
        descripcion=actividad.descripcion,
        ubicacion=actividad.ubicacion,
        fecha_actividad=actividad.fecha_actividad,
        horas_asignar=actividad.horas_asignar,
        hora_inicio=actividad.hora_inicio,
        hora_final=actividad.hora_final,
        cupos=actividad.cupos,
        cupos_disponibles=_cupos_disponibles(actividad.id, actividad.cupos, db),
        estado=actividad.estado.nombre_estado if actividad.estado else "Programada"
    )

def eliminar_actividad_controller(actividad_id: int, db: Session):
    # 1. Buscar la actividad
    actividad = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    # 2. Validar que la actividad sea en el futuro (antes del evento o el mismo día)
    hoy = date.today()
    if actividad.fecha_actividad < hoy:
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar una actividad cuya fecha ya pasó"
        )

    # 3. Eliminar la actividad
    db.delete(actividad)
    db.commit()
    return {"mensaje": "Actividad eliminada exitosamente"}

