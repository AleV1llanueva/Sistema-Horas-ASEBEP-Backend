from fastapi import APIRouter, Depends, Request, File, Form, UploadFile
from sqlalchemy.orm import Session
from utils.database import get_db
from schemas.aportacion import AportacionResponse, RevisionAportacionInput
from controllers.aportacion_controller import (
    crear_aportacion_controller,
    mis_aportaciones_controller,
    listar_aportaciones_pendientes_controller,
    revisar_aportacion_controller
)
from core.security import becario, admin_aportaciones

router = APIRouter()

# Subir aportación
@router.post("/aportaciones", response_model=AportacionResponse, tags=["Aportaciones"])
@becario
def crear_aportacion(
    request: Request,
    num_referencia: str = Form(...),
    descripcion: str = Form(...),
    archivo_pdf: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    num_cuenta = request.state.num_cuenta
    return crear_aportacion_controller(
        num_cuenta=num_cuenta, 
        num_referencia=num_referencia, 
        descripcion=descripcion,  # <--- Pasado al controlador
        archivo_pdf=archivo_pdf, 
        db=db
    )

# Ver mis aportaciones (Becario)
@router.get("/becario/aportaciones", response_model=list[AportacionResponse], tags=["Aportaciones"])
@becario
def ver_mis_aportaciones(
    request: Request,
    db: Session = Depends(get_db)
):
    num_cuenta = request.state.num_cuenta
    return mis_aportaciones_controller(num_cuenta, db)

# Ver aportaciones pendientes de revisión (Administrador)
@router.get("/aportaciones/pendientes", response_model=list[AportacionResponse], tags=["Aportaciones"])
@admin_aportaciones
def ver_aportaciones_pendientes(
    request: Request,
    db: Session = Depends(get_db)
):
    return listar_aportaciones_pendientes_controller(db)

# Aprobar o rechazar aportación (Administrador)
@router.put("/aportaciones/{aportacion_id}", tags=["Aportaciones"])
@admin_aportaciones
def revisar_aportacion(
    request: Request,
    aportacion_id: int,
    data: RevisionAportacionInput,
    db: Session = Depends(get_db),
):
    return revisar_aportacion_controller(
        aportacion_id=aportacion_id, 
        nombre_estado=data.estado, 
        meses_aprobados=data.meses_aprobados, 
        db=db
    )
