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
@router.post("/asistencias/actividades/{actividad_id}", response_model=InscripcionResponse, tags=["Asistencias"])
@becario
def inscribirse(request: Request, actividad_id: int, db: Session = Depends(get_db)):
    num_cuenta = request.state.num_cuenta
    return inscribirse_controller(InscripcionInput(actividad_id=actividad_id), num_cuenta, db)

#Cancelar Actividad
@router.delete("/asistencias/actividades/{actividad_id}", tags=["Asistencias"])
@becario
def cancelar_inscripcion(request: Request, actividad_id: int, db: Session = Depends(get_db)):
    num_cuenta = request.state.num_cuenta
    return cancelar_inscripcion_controller(actividad_id, num_cuenta, db)

#Ver mis inscripciones
@router.get("/asistencias", response_model=List[MisInscripcionesResponse], tags=["Asistencias"])
@becario
def mis_inscripciones(request: Request, db: Session = Depends(get_db)):
    num_cuenta = request.state.num_cuenta
    return mis_inscripciones_controller(num_cuenta, db)

#QR entrada para asistencia
@router.post("/asistencias/entrada/actividades/{actividad_id}", tags=["Asistencias"])
@admin_horas
def generar_qr_entrada(request: Request, actividad_id: int, db: Session = Depends(get_db)):
    qr_bytes = generar_qr_entrada_controller(actividad_id, db)
    return Response(content=qr_bytes, media_type="image/png", headers={
        "Content-Disposition": f"attachment; filename=qr_entrada_{actividad_id}.png"
    })

#QR salida para asistencia
@router.post("/asistencias/salida/actividades/{actividad_id}", tags=["Asistencias"])
@admin_horas
def generar_qr_salida(request: Request, actividad_id: int, db: Session = Depends(get_db)):
    qr_bytes = generar_qr_salida_controller(actividad_id, db)
    return Response(content=qr_bytes, media_type="image/png", headers={
        "Content-Disposition": f"attachment; filename=qr_salida_{actividad_id}.png"
    })


#Escanear QR entrada
@router.get("/asistencias/entrada", tags=["Asistencias"])
@becario
def registrar_entrada_qr(request: Request, token: str, db: Session = Depends(get_db)):
    num_cuenta = request.state.num_cuenta
    return registrar_entrada_qr_controller(token, num_cuenta, db)

#Escanear QR salida 
@router.get("/asistencias/salida", tags=["Asistencias"])
@becario
def registrar_salida_qr(request: Request, token: str, db: Session = Depends(get_db)):
    num_cuenta = request.state.num_cuenta
    return registrar_salida_qr_controller(token, num_cuenta, db)

#Asistencia Manual entrada
@router.post("/asistencias/entrada/actividades/{actividad_id}/becario/{num_cuenta}", tags=["Asistencias"])
@admin_horas
def registrar_entrada_manual(request: Request, actividad_id: int, num_cuenta: str, db: Session = Depends(get_db)):
    return registrar_entrada_manual_controller(actividad_id, num_cuenta, db)

#Asistencia Manual salida
@router.post("/asistencias/salida/actividades/{actividad_id}/becario/{num_cuenta}", tags=["Asistencias"])
@admin_horas
def registrar_salida_manual(request: Request, actividad_id: int, num_cuenta: str, db: Session = Depends(get_db)):
    return registrar_salida_manual_controller(actividad_id, num_cuenta, db)

#Ver todas las asistencias
@router.get("/asistencias/actividades/{actividad_id}", tags=["Asistencias"])
@admin_horas
def ver_lista_asistencia(request: Request, actividad_id: int, db: Session = Depends(get_db)):
    return ver_lista_asistencia_controller(actividad_id, db)