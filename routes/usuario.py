from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from utils.database import get_db
from schemas.usuario import CrearUsuario, UsuarioResponse
from controllers.usuario_controller import crear_usuario_controller
from core.security import admin_general

router = APIRouter()

@router.post("/usuarios", response_model=UsuarioResponse, tags=["Usuarios"])
@admin_general

async def crear_usuario(request: Request, data: CrearUsuario, db:Session = Depends(get_db)):
    return crear_usuario_controller(data, db)