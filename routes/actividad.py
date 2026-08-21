# routes/actividad.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import List
from utils.database import get_db
from schemas.actividad import CrearActividadInput, ActividadResponse
from controllers.actividad_controller import crear_actividad_controller, ver_actividades_controller
from core.security import admin_horas, cualquier_usuario

router = APIRouter()

@router.post("/actividades", response_model=ActividadResponse, tags=["Actividades"])
@admin_horas
async def crear_actividad(request: Request, data: CrearActividadInput, db: Session = Depends(get_db)):
    return crear_actividad_controller(data, db)

@router.get("/actividades", response_model=List[ActividadResponse], tags=["Actividades"])
@cualquier_usuario
async def ver_actividades(request: Request, db: Session = Depends(get_db)):
    return ver_actividades_controller(db)