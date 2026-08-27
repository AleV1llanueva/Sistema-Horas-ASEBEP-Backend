from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
from typing import List
from utils.database import get_db
from schemas.asistencia import InscripcionInput, InscripcionResponse, MisInscripcionesResponse
from controllers.asistencia_controller import (
    inscribirse_controller, 
    cancelar_inscripcion_controller, 
    mis_inscripciones_controller,
    generar_qr_entrada_controller,
    generar_qr_salida_controller,
    registrar_entrada_qr_controller,
    registrar_salida_qr_controller,
    registrar_entrada_manual_controller,
    registrar_salida_manual_controller,
    ver_lista_asistencia_controller
)
from core.security import becario, admin_horas

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

# QR

@router.post("/actividades/{actividad_id}/qr/entrada", tags=["Asistencias"])
@admin_horas
async def generar_qr_entrada(request: Request, actividad_id: int, db: Session = Depends(get_db)):
    qr_bytes = generar_qr_entrada_controller(actividad_id, db)
    return Response(content=qr_bytes, media_type="image/png", headers={
        "Content-Disposition": f"attachment; filename=qr_entrada_{actividad_id}.png"
    })

@router.post("/actividades/{actividad_id}/qr/salida", tags=["Asistencias"])
@admin_horas
async def generar_qr_salida(request: Request, actividad_id: int, db: Session = Depends(get_db)):
    qr_bytes = generar_qr_salida_controller(actividad_id, db)
    return Response(content=qr_bytes, media_type="image/png", headers={
        "Content-Disposition": f"attachment; filename=qr_salida_{actividad_id}.png"
    })

@router.get("/asistencia/entrada", tags=["Asistencias"])
@becario
async def registrar_entrada_qr(request: Request, token: str, db: Session = Depends(get_db)):
    num_cuenta = request.state.num_cuenta
    return registrar_entrada_qr_controller(token, num_cuenta, db)

@router.get("/asistencia/salida", tags=["Asistencias"])
@becario
async def registrar_salida_qr(request: Request, token: str, db: Session = Depends(get_db)):
    num_cuenta = request.state.num_cuenta
    return registrar_salida_qr_controller(token, num_cuenta, db)

# --- Manual ---
@router.post("/actividades/{actividad_id}/asistencia/entrada/{num_cuenta}", tags=["Asistencias"])
@admin_horas
async def registrar_entrada_manual(request: Request, actividad_id: int, num_cuenta: str, db: Session = Depends(get_db)):
    return registrar_entrada_manual_controller(actividad_id, num_cuenta, db)


@router.post("/actividades/{actividad_id}/asistencia/salida/{num_cuenta}", tags=["Asistencias"])
@admin_horas
async def registrar_salida_manual(request: Request, actividad_id: int, num_cuenta: str, db: Session = Depends(get_db)):
    return registrar_salida_manual_controller(actividad_id, num_cuenta, db)

# --- Ver lista asistencia ---
@router.get("/actividades/{actividad_id}/asistencia", tags=["Asistencias"])
@admin_horas
async def ver_lista_asistencia(request: Request, actividad_id: int, db: Session = Depends(get_db)):
    return ver_lista_asistencia_controller(actividad_id, db)