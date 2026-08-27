from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import List
from utils.database import get_db
from schemas.multa import RegistrarMultaInput, MultaResponse
from controllers.multa_controller import (
    registrar_multa_controller,
    ver_multas_becario_controller,
    ver_todas_multas_controller
)
from core.security import admin_aportaciones, becario, admin_general

router = APIRouter()

@router.post("/multas", response_model=MultaResponse, tags=["Multas"])
@admin_aportaciones
async def registrar_multa(request: Request, data: RegistrarMultaInput, db: Session = Depends(get_db)):
    return registrar_multa_controller(data, db)

@router.get("/becario/multas", response_model=List[MultaResponse], tags=["Multas"])
@becario
async def ver_mis_multas(request: Request, db: Session = Depends(get_db)):
    num_cuenta = request.state.num_cuenta
    return ver_multas_becario_controller(num_cuenta, db)

@router.get("/multas", response_model=List[MultaResponse], tags=["Multas"])
@admin_aportaciones
async def ver_todas_multas(request: Request, db: Session = Depends(get_db)):
    return ver_todas_multas_controller(db)