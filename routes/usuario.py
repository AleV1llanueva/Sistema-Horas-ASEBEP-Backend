import requests
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from utils.database import get_db

from schemas.usuario import CrearUsuario, UsuarioResponse
from schemas.becario import LoginResponse, BecarioGeneralResponse

from controllers.usuario_controller import crear_usuario_controller
from controllers.becario_controller import user_controller, obtener_todos_los_becarios_controller
from core.security import admin_general, cualquier_usuario, solo_administradores

router = APIRouter()

@router.get("/usuarios", response_model=list[BecarioGeneralResponse], tags=["Usuarios"])
@solo_administradores  # O el decorador que restrinja únicamente a administradores
async def obtener_todos_los_becarios(request: Request, db: Session = Depends(get_db)):
    return obtener_todos_los_becarios_controller(db)

@router.get("/usuario/{num_cuenta}", response_model=LoginResponse, tags=["Usuarios"])
@cualquier_usuario
async def obtener_usuario(request: Request, num_cuenta: str, db: Session = Depends(get_db)):
    return user_controller(num_cuenta, request, db)

@router.post("/usuarios", response_model=UsuarioResponse, tags=["Usuarios"])
@admin_general
async def crear_usuario(request: Request, data: CrearUsuario, db:Session = Depends(get_db)):
    return crear_usuario_controller(data, db)