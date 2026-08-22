from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.usuario import Usuario 
from models.rol import Rol
from models.carrera import Carrera
from schemas.usuario import CrearUsuario, UsuarioResponse


def crear_usuario_controller(data: CrearUsuario, db: Session) -> UsuarioResponse:
    #Verificar que el rol existe
    rol = db.query(Rol).filter(Rol.id == data.rol_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    #Verificar que la carrera que existe
    carrera = db.query(Carrera).filter(Carrera.id == data.carrera_id).first()
    if not carrera:
        raise HTTPException(status_code=404, detail="Carrera no encontrada")

    #Verificar que el número de cuenta no exista
    usuario_existente = db.query(Usuario).filter(Usuario.num_cuenta == data.num_cuenta).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="El número de cuenta ya está registrado")

    #Verificar que el correo no exista ya 
    correo_existente = db.query(Usuario).filter(Usuario.correo_institucional == data.correo_institucional).first()
    if correo_existente:
        raise HTTPException(status_code=400, detail="El correo instituciona ya está registrado")

    #Crear usuario sin contraseña y sin activar
    nuevo_usuario = Usuario(
        num_cuenta = data.num_cuenta,
        primer_nombre=data.primer_nombre,
        segundo_nombre=data.segundo_nombre,
        primer_apellido=data.primer_apellido,
        segundo_apellido=data.segundo_apellido,
        correo_institucional=data.correo_institucional,
        correo_personal=data.correo_personal,
        telefono=data.telefono,
        carrera_id=data.carrera_id,
        rol_id=data.rol_id,
        password_hash=None,
        active=False
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return UsuarioResponse(
        num_cuenta=str(nuevo_usuario.num_cuenta),
        primer_nombre=nuevo_usuario.primer_nombre,
        primer_apellido=nuevo_usuario.primer_apellido,
        correo_institucional=nuevo_usuario.correo_institucional,
        rol_id=nuevo_usuario.rol_id,
        active=nuevo_usuario.active
    )