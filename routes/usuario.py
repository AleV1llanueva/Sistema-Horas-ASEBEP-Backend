from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from utils.database import get_db

from schemas.usuario import CrearUsuario, UsuarioResponse, ActualizarUsuarioInput
from schemas.becario import LoginResponse, BecarioGeneralResponse

from controllers.usuario_controller import crear_usuario_controller, actualizar_usuario_por_admin_controller
from controllers.becario_controller import user_controller, obtener_todos_los_becarios_controller
from core.security import admin_general, becario, solo_administradores, admin_general

router = APIRouter()

#Ver todos los usuarios
@router.get("/usuarios", response_model=list[BecarioGeneralResponse], tags=["Usuarios"])
@solo_administradores 
def obtener_todos_los_becarios(request: Request, db: Session = Depends(get_db)):
    return obtener_todos_los_becarios_controller(db)

#Ver perfil becario de un usuario especifico 
@router.get("/usuarios/{num_cuenta}", response_model=LoginResponse, tags=["Usuarios"])
@becario
def obtener_usuario(request: Request, num_cuenta: str, db: Session = Depends(get_db)):
    return user_controller(num_cuenta, request, db)

#Agregar un usuario nuevo
@router.post("/usuarios", response_model=UsuarioResponse, tags=["Usuarios"])
@admin_general
def crear_usuario(request: Request, data: CrearUsuario, db:Session = Depends(get_db)):
    return crear_usuario_controller(data, db)

#Editar usuario
@router.put("/usuarios/{num_cuenta}", tags=["Usuarios"])
@admin_general
def actualizar_usuario_admin(
    request: Request,
    num_cuenta: str,
    data: ActualizarUsuarioInput,
    db: Session = Depends(get_db)
):
    return actualizar_usuario_por_admin_controller(num_cuenta, data, db)
