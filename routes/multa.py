from fastapi import APIRouter, Depends, Request, File, Form, UploadFile
from sqlalchemy.orm import Session
from typing import List
from utils.database import get_db
from schemas.multa import RegistrarMultaInput, MultaResponse
from schemas.aportacion import RevisionAportacionInput
from controllers.multa_controller import (
    registrar_multa_controller,
    ver_multas_becario_controller,
    ver_todas_multas_controller,
    enviar_pago_multa_controller,
    revisar_pago_multa_controller,
    ver_todos_comprobantes_multas_controller,
    ver_mis_comprobantes_multas_controller
)
from core.security import admin_aportaciones, becario, admin_general, admin_horas

router = APIRouter()

#Asignar Multa
@router.post("/multas", response_model=MultaResponse, tags=["Multas"])
@admin_aportaciones
def registrar_multa(request: Request, data: RegistrarMultaInput, db: Session = Depends(get_db)):
    return registrar_multa_controller(data, db)

#Ver lista de Multas 
@router.get("/becario/multas", response_model=List[MultaResponse], tags=["Multas"])
@becario
def ver_mis_multas(request: Request, db: Session = Depends(get_db)):
    num_cuenta = request.state.num_cuenta
    return ver_multas_becario_controller(num_cuenta, db)

#Ver lista de Multas Admiin
@router.get("/multas", response_model=List[MultaResponse], tags=["Multas"])
@admin_aportaciones
def ver_todas_multas(request: Request, db: Session = Depends(get_db)):
    return ver_todas_multas_controller(db)

#subir comprobante de la multa
@router.post("/multas/{multa_id}/comprobantes", tags=["Multas"])
@becario
def pagar_multa(
    request: Request,
    multa_id: int,
    num_referencia: str = Form(...),
    archivo_pdf: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    num_cuenta = request.state.num_cuenta
    return enviar_pago_multa_controller(multa_id, num_cuenta, num_referencia, archivo_pdf, db)

# El administrador revisa (aprueba/rechaza) el comprobante de la multa
@router.put("/multas/comprobantes/{comprobante_id}", tags=["Multas"])
@admin_horas
def revisar_pago_multa(
    request: Request,
    comprobante_id: int,
    data: RevisionAportacionInput, 
    db: Session = Depends(get_db)
):
    return revisar_pago_multa_controller(comprobante_id, data.estado, db)

#ver todos los comprobantes
@router.get("/multas/comprobantes", tags=["Multas"])
@admin_horas
def ver_todos_comprobantes(request: Request, db: Session = Depends(get_db)):
    return ver_todos_comprobantes_multas_controller(db)

#ver todos mis comprobantes como becario
@router.get("/becario/multas/comprobantes", tags=["Multas"])
@becario
def ver_mis_comprobantes(request: Request, db: Session = Depends(get_db)):
    num_cuenta = request.state.num_cuenta
    return ver_mis_comprobantes_multas_controller(num_cuenta, db)
