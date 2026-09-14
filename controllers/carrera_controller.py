from sqlalchemy.orm import Session 
from fastapi import HTTPException
from models.carrera import Carrera
from schemas.carrera import CarreraInput
from utils.texto import normalizar_texto

def crear_carrera_controller(carrera:  CarreraInput, db:Session):
    nombre_normalizado = normalizar_texto(carrera.nombre_carrera)

    carreras_existentes = db.query(Carrera).all()
    for c in carreras_existentes:
        if normalizar_texto(c.nombre_carrera) == nombre_normalizado:
            raise HTTPException(
                status_code=400,
                detail="Ya existe una carrera con ese nombre"
            )
        
    nueva_carrera = Carrera(nombre_carrera = carrera.nombre_carrera)
    db.add(nueva_carrera)
    db.commit()
    db.refresh(nueva_carrera)
    return nueva_carrera

def obtener_carreras_controller(db:Session):
    return db.query(Carrera).all()

def obtener_carrera_por_id_controller(carrera_id: int, db:Session):
    carrera = db.query(Carrera).filter(
        Carrera.id == carrera_id
    ).first()
    if not carrera:
        raise HTTPException(
            status_code=404,
            detail="Carrera no encontrada"
        )
    return carrera

def actualizar_carrera_controller(carrera_id: int, datos: CarreraInput, db: Session):
    carrera = db.query(Carrera).filter(Carrera.id == carrera_id).first()
    if not carrera:
        raise HTTPException(status_code=404, detail="Carrera no encontrada")

    nombre_normalizado = normalizar_texto(datos.nombre_carrera)
    carreras_existentes = db.query(Carrera).filter(Carrera.id != carrera_id).all()
    for c in carreras_existentes:
        if normalizar_texto(c.nombre_carrera) == nombre_normalizado:
            raise HTTPException(
                status_code=400,
                detail="Ya existe una carrera con ese nombre"
            )

    carrera.nombre_carrera = datos.nombre_carrera
    db.commit()
    db.refresh(carrera)
    return carrera

def desactivar_carrera_controller(carrera_id: int, db: Session):
    carrera = db.query(Carrera).filter(
        Carrera.id == carrera_id, Carrera.activo == True
    ).first()
    if not carrera:
        raise HTTPException(
            status_code=404,
            detail="Carrera no encontrada o ya está desactivada"
        )
    carrera.activo = False
    db.commit()
    return {"mensjae": "Carrera desactivada exitosamente"}

def activar_carrera_controller(carrera_id: int, db: Session):
    carrera = db.query(Carrera).filter(Carrera.id == carrera_id).first()
    if not carrera:
        raise HTTPException(status_code=404, detail="Carrera no encontrada")
    if carrera.activo:
        raise HTTPException(status_code=400, detail="La carrera ya está activa")
    carrera.activo = True
    db.commit()
    db.refresh(carrera)
    return carrera