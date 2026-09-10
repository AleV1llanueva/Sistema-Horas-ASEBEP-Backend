# routes/actividad.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import List
from utils.database import get_db
from schemas.actividad import CrearActividadInput, ActividadResponse
from controllers.actividad_controller import (
    crear_actividad_controller, 
    ver_actividades_controller, 
    editar_actividad_controller,
    eliminar_actividad_controller
)
from core.security import admin_horas, cualquier_usuario

router = APIRouter()

#Crear Actividad
@router.post("/actividades", response_model=ActividadResponse, tags=["Actividades"])
@admin_horas
def crear_actividad(request: Request, data: CrearActividadInput, db: Session = Depends(get_db)):
    return crear_actividad_controller(data, db)

#Ver Actividades
@router.get("/actividades", response_model=List[ActividadResponse], tags=["Actividades"])
@cualquier_usuario
def ver_actividades(request: Request, db: Session = Depends(get_db)):
    return ver_actividades_controller(db)

#Editar Actividad
@router.put("/actividades/{actividad_id}", tags=["Actividades"])
@admin_horas
def editar_actividad(
    request: Request,
    actividad_id: int,
    data: CrearActividadInput,
    db: Session = Depends(get_db)
):
    return editar_actividad_controller(actividad_id, data, db)

#Eliminar Actividad
@router.delete("/actividades/{actividad_id}", tags=["Actividades"])
@admin_horas
def eliminar_actividad(
    request: Request,
    actividad_id: int,
    db: Session = Depends(get_db)
):
    return eliminar_actividad_controller(actividad_id, db)


