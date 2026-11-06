from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from utils.database import get_db

from schemas.usuario import AsignarCorreoInstitucionalInput, CrearUsuario, UsuarioResponse, ActualizarUsuarioInput
from schemas.becario import BecariosPaginadosResponse, BecarioGeneralSinCorreoResponse, LoginResponse, BecarioGeneralResponse, BecarioUpdateInput, DatosBecario

from controllers.usuario_controller import (
    crear_usuario_controller,
    actualizar_usuario_por_admin_controller,
    asignar_correo_institucional_controller,
    consultar_disponibilidad_controller,
    eliminar_estudiante_controller,
)
from controllers.becario_controller import (
    actualizar_becario_por_admin_controller,
    obtener_becarios_sin_correo_controller,
    user_controller,
    obtener_todos_los_becarios_controller,
    usuario_me_controller,
    desactivar_becario_controller,
    reactivar_becario_controller,
    actualizar_becario_controller
)
from core.security import admin_general, becario, solo_administradores, admin_general, cualquier_usuario

router = APIRouter()

#Ver todos los usuarios
# Sin pagina ni limite devuelve la lista completa (contrato anterior).
# Con ambos parámetros devuelve una página junto con los totales.
@router.get(
    "/usuarios",
    response_model=list[BecarioGeneralResponse] | BecariosPaginadosResponse,
    tags=["Usuarios"],
)
@solo_administradores
def obtener_todos_los_becarios(
    request: Request,
    pagina: int | None = Query(default=None, ge=1, description="Página solicitada (1-based)"),
    limite: int | None = Query(default=None, ge=1, le=100, description="Registros por página (máximo 100)"),
    busqueda: str | None = Query(default=None, description="Filtro por nombre, cuenta, carrera o correo"),
    active: bool | None = Query(default=None, description="Filtra por estado de la cuenta (true/false)"),
    db: Session = Depends(get_db),
):
    resultado = obtener_todos_los_becarios_controller(
        db,
        pagina=pagina,
        limite=limite,
        busqueda=busqueda,
        activo=active,
    )

    if pagina is None or limite is None:
        return resultado.elementos

    return resultado

@router.get("/usuarios/sin-correo", response_model=list[BecarioGeneralSinCorreoResponse], tags=["Usuarios"])
@solo_administradores
def obtener_becarios_sin_correo(request: Request, db: Session = Depends(get_db)):
    return obtener_becarios_sin_correo_controller(db)

# Comprobación previa del alta: indica si la cuenta o el correo ya existen.
# Solo devuelve un booleano, sin datos personales.
# Se declara antes de /usuarios/{num_cuenta} para que no la capture.
@router.get("/usuarios/disponibilidad", tags=["Usuarios"])
@solo_administradores
def consultar_disponibilidad(
    request: Request,
    num_cuenta: str | None = Query(default=None),
    correo_institucional: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if not num_cuenta and not correo_institucional:
        raise HTTPException(
            status_code=400,
            detail="Indica el número de cuenta o el correo institucional",
        )

    return consultar_disponibilidad_controller(
        db,
        num_cuenta=num_cuenta,
        correo_institucional=correo_institucional,
    )

#Ver perfil becario propio
@router.get("/usuarios/me", tags=["Usuarios"])
@cualquier_usuario
def obtener_mi_info(request: Request, db: Session = Depends(get_db)):
    return usuario_me_controller(request, db)

#Ver perfil becario de un usuario especifico
@router.get("/usuarios/{num_cuenta}", response_model=LoginResponse, tags=["Usuarios"])
@admin_general
def obtener_usuario(request: Request, num_cuenta: str, db: Session = Depends(get_db)):
    return user_controller(num_cuenta, request, db)

#Agregar un usuario nuevo
@router.post("/usuarios", response_model=UsuarioResponse, tags=["Usuarios"])
@admin_general
def crear_usuario(request: Request, data: CrearUsuario, db:Session = Depends(get_db)):
    return crear_usuario_controller(data, db)

# Asignar o corregir el correo institucional de un usuario sin correo
@router.patch("/usuarios/{num_cuenta}/correo", tags=["Usuarios"])
@admin_general
def asignar_correo_institucional(
    request: Request,
    num_cuenta: str,
    data: AsignarCorreoInstitucionalInput,
    db: Session = Depends(get_db),
):
    return asignar_correo_institucional_controller(num_cuenta, data, db)

# Eliminar definitivamente a un estudiante (solo si no tiene registros)
@router.delete("/usuarios/{num_cuenta}", tags=["Usuarios"])
@admin_general
def eliminar_usuario(request: Request, num_cuenta: str, db: Session = Depends(get_db)):
    return eliminar_estudiante_controller(num_cuenta, db)

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

# Desactivar becario
@router.delete("/becarios/{num_cuenta}", tags=["Becarios"])
@admin_general
def desactivar_becario(request: Request, num_cuenta: str, db: Session = Depends(get_db)):
    return desactivar_becario_controller(num_cuenta, db)


# Reactivar becario
@router.patch("/becarios/{num_cuenta}", tags=["Becarios"])
@admin_general
def reactivar_becario(request: Request, num_cuenta: str, db: Session = Depends(get_db)):
    return reactivar_becario_controller(num_cuenta, db)

# Ajustes de horas, aportaciones y periodo de ingreso.
# Exclusivo del administrador general: los datos previos al sistema
# solo pueden corregirse desde este rol.
@router.patch(
    "/becarios/{num_cuenta}/datos-academicos",
    response_model=DatosBecario,
    tags=["Becarios"],
)
@admin_general
def actualizar_datos_academicos_becario(
    request: Request,
    num_cuenta: str,
    datos: BecarioUpdateInput,
    db: Session = Depends(get_db),
):
    return actualizar_becario_por_admin_controller(num_cuenta, datos, db)

#Editar perfil becario
@router.put("/becarios/{num_cuenta}", response_model=DatosBecario, tags=["Becarios"])
@admin_general
def actualizar_becario(request: Request, num_cuenta: str, datos: BecarioUpdateInput, db: Session = Depends(get_db)):
    return actualizar_becario_controller(num_cuenta, datos, db)
