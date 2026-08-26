from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.usuario import Usuario 
from models.becario import Becario
from models.rol import Rol
from models.carrera import Carrera
from schemas.usuario import CrearUsuario, UsuarioResponse
from schemas.becario import PerfilBecarioResponse


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

    try:
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
        db.flush()

        #calcular el periodo 
        if data.mes_inicio <= 5:
            pac = "I-PAC"
        elif data.mes_inicio <= 8:
            pac = "II-PAC"
        else:
            pac = "III-PAC"

        #crear el perfil becario
        nuevo_perfil_becario = Becario(
            num_cuenta = data.num_cuenta,
            periodo_inicio = pac,
            anio_inicio = data.anio_inicio,
            mes_inicio = data.mes_inicio,
            horas_acumuladas = 0,
            monto_acumulado = 0,
            estado_beca_id = 1
        )
        db.add(nuevo_perfil_becario)

        db.commit()
        db.refresh(nuevo_usuario)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar el usuario y su perfil: {str(e)}")

    return UsuarioResponse(
        num_cuenta=str(nuevo_usuario.num_cuenta),
        primer_nombre=nuevo_usuario.primer_nombre,
        primer_apellido=nuevo_usuario.primer_apellido,
        correo_institucional=nuevo_usuario.correo_institucional,
        rol_id=nuevo_usuario.rol_id,
        active=nuevo_usuario.active,
        perfil_becario=PerfilBecarioResponse(
            periodo_inicio=nuevo_perfil_becario.periodo_inicio,
            anio_inicio=nuevo_perfil_becario.anio_inicio,
            mes_inicio=nuevo_perfil_becario.mes_inicio,
            horas_acumuladas=nuevo_perfil_becario.horas_acumuladas,
            monto_acumulado=nuevo_perfil_becario.monto_acumulado
        )
    )