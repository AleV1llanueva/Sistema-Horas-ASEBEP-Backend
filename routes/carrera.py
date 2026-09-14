from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from utils.database import get_db
from schemas.carrera import CarreraInput, CarreraResponse
from controllers.carrera_controller import (
    crear_carrera_controller,
    obtener_carreras_controller,
    obtener_carrera_por_id_controller,
    actualizar_carrera_controller,
    desactivar_carrera_controller,
    activar_carrera_controller
)
from core.security import admin_general

router = APIRouter()


@router.post("/carreras", response_model=CarreraResponse, status_code=201, tags=["Carreras"])
@admin_general
def crear_carrera(request: Request, carrera: CarreraInput, db: Session = Depends(get_db)):
    return crear_carrera_controller(carrera, db)


@router.get("/carreras", response_model=list[CarreraResponse], tags=["Carreras"])
@admin_general
def obtener_carreras(request: Request, db: Session = Depends(get_db)):
    return obtener_carreras_controller(db)


@router.get("/carreras/{carrera_id}", response_model=CarreraResponse, tags=["Carreras"])
@admin_general
def obtener_carrera(request: Request, carrera_id: int, db: Session = Depends(get_db)):
    return obtener_carrera_por_id_controller(carrera_id, db)


@router.put("/carreras/{carrera_id}", response_model=CarreraResponse, tags=["Carreras"])
@admin_general
def actualizar_carrera(request: Request, carrera_id: int, datos: CarreraInput, db: Session = Depends(get_db)):
    return actualizar_carrera_controller(carrera_id, datos, db)


@router.delete("/carreras/{carrera_id}", tags=["Carreras"])
@admin_general
def desactivar_carrera(request: Request, carrera_id: int, db: Session = Depends(get_db)):
    return desactivar_carrera_controller(carrera_id, db)

@router.patch("/carreras/{carrera_id}", response_model=CarreraResponse, tags=["Carreras"])
@admin_general
def activar_carrera(request: Request, carrera_id: int, db: Session = Depends(get_db)):
    return activar_carrera_controller(carrera_id, db)