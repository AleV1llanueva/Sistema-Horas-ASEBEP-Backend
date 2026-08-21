from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import List
from utils.database import get_db
from schemas.asistencia import InscripcionInput, InscripcionResponse, MisInscripcionesResponse
from controllers.asistencia_controller import inscribirse_controller, cancelar_inscripcion_controller, mis_inscripciones_controller
from core.security import becario

router = APIRouter()

#Inscribirse Actividad
@router.post("/actividades/{actividad_id}/inscripcion", response_model=InscripcionResponse, tags=["Asistencias"])
@becario
async def inscribirse(request: Request, actividad_id: int, db: Session = Depends(get_db)):
    num_cuenta = request.state.num_cuenta
    return inscribirse_controller(InscripcionInput(actividad_id=actividad_id), num_cuenta, db)

#Cancelar Actividad
@router.delete("/actividades/{actividad_id}/inscripcion", tags=["Asistencias"])
@becario
async def cancelar_inscripcion(request: Request, actividad_id: int, db: Session = Depends(get_db)):
    num_cuenta = request.state.num_cuenta
    return cancelar_inscripcion_controller(actividad_id, num_cuenta, db)

#Ver mis inscripciones
@router.get("/becario/inscripciones", response_model=List[MisInscripcionesResponse], tags=["Asistencias"])
@becario
async def mis_inscripciones(request: Request, db: Session = Depends(get_db)):
    num_cuenta = request.state.num_cuenta
    return mis_inscripciones_controller(num_cuenta, db)