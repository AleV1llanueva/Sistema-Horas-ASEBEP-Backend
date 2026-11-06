from fastapi import HTTPException
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from models.usuario import Usuario 
from models.becario import Becario
from models.rol import Rol
from models.carrera import Carrera
from models.asistencia import Asistencia
from models.aportacion import Aportacion
from models.multa import Multa
from models.comprobantes_multa import ComprobanteMulta
from models.pagos import Pago
from models.pin_activacion import PinActivacion
from models.pin_intentos import PinIntentos
from schemas.usuario import AsignarCorreoInstitucionalInput, CrearUsuario, UsuarioResponse
from schemas.becario import PerfilBecarioResponse
from controllers.becario_controller import obtener_estado_beca_id

# Rol que se asigna automáticamente a los becarios creados desde el panel.
ROL_BECARIO = "Becario"

# Tablas que guardan datos del estudiante y qué se informa cuando lo bloquean.
# Sin referencias en ninguna, el estudiante se puede borrar del todo.
REFERENCIAS_DEL_ESTUDIANTE = [
    (Asistencia, "asistencias", "inscripciones a actividades"),
    (Aportacion, "aportaciones", "aportaciones registradas"),
    (Multa, "multas", "multas registradas"),
    (ComprobanteMulta, "comprobantes_multas", "comprobantes de multa"),
    (Pago, "pagos", "pagos registrados"),
]

def obtener_rol_becario(db: Session) -> Rol:
    """
    Devuelve el rol que corresponde a los estudiantes becarios.

    Se busca por nombre en lugar de asumir un identificador fijo,
    para que el alta funcione aunque la tabla de roles no empiece en 1.
    """
    rol = (
        db.query(Rol)
        .filter(func.lower(Rol.nombre_rol) == ROL_BECARIO.lower())
        .first()
    )

    if not rol:
        raise HTTPException(
            status_code=500,
            detail=f"El rol '{ROL_BECARIO}' no está configurado en el sistema",
        )

    return rol


def detalle_duplicado(campo: str, usuario: Optional[Usuario]) -> dict:
    """
    Indica qué dato impedía crear al estudiante y a quién pertenece.

    La interfaz usa `num_cuenta` para ofrecer un enlace al registro
    existente, por eso se envía como parte del detalle.
    """
    if usuario is None:
        # El registro se liberó entre el intento y la consulta.
        return {
            "mensaje": (
                "El número de cuenta ya está registrado"
                if campo == "num_cuenta"
                else "El correo institucional ya está registrado"
            ),
            "campo": campo,
        }

    return {
        "mensaje": (
            "El número de cuenta ya está registrado"
            if campo == "num_cuenta"
            else "El correo institucional ya está registrado"
        ),
        "campo": campo,
        "num_cuenta": usuario.num_cuenta,
        "nombre_completo": " ".join(
            parte
            for parte in (
                usuario.primer_nombre,
                usuario.segundo_nombre,
                usuario.primer_apellido,
                usuario.segundo_apellido,
            )
            if parte
        ),
        "correo_institucional": usuario.correo_institucional,
    }


def crear_usuario_controller(data: CrearUsuario, db: Session) -> UsuarioResponse:
    # El rol de un estudiante siempre es el de becario.
    rol_becario = obtener_rol_becario(db)

    # Si el cliente envía un rol, debe coincidir con el de becario.
    if data.rol_id is not None and data.rol_id != rol_becario.id:
        raise HTTPException(
            status_code=400,
            detail=f"El rol asignado debe ser '{rol_becario.nombre_rol}'",
        )

    #Verificar que la carrera que existe
    carrera = db.query(Carrera).filter(Carrera.id == data.carrera_id).first()
    if not carrera:
        raise HTTPException(status_code=404, detail="Carrera no encontrada")

    #Verificar que el número de cuenta no exista
    usuario_existente = db.query(Usuario).filter(Usuario.num_cuenta == data.num_cuenta).first()
    if usuario_existente:
        raise HTTPException(
            status_code=409,
            detail=detalle_duplicado("num_cuenta", usuario_existente),
        )

    #Verificar que el correo no exista ya 
    correo_existente = db.query(Usuario).filter(Usuario.correo_institucional == data.correo_institucional).first()
    if correo_existente:
        raise HTTPException(
            status_code=409,
            detail=detalle_duplicado("correo_institucional", correo_existente),
        )

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
            rol_id=rol_becario.id,
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
            estado_beca_id = obtener_estado_beca_id("Activo", db)
        )
        db.add(nuevo_perfil_becario)

        db.commit()
        db.refresh(nuevo_usuario)

    except Exception as e:
        db.rollback()
        # La cuenta o el correo pueden repetirse entre el chequeo y el commit.
        if es_error_de_duplicado(e):
            repetido = db.query(Usuario).filter(
                or_(
                    Usuario.num_cuenta == data.num_cuenta,
                    Usuario.correo_institucional == data.correo_institucional,
                )
            ).first()
            campo = (
                "num_cuenta"
                if repetido and repetido.num_cuenta == data.num_cuenta
                else "correo_institucional"
            )
            raise HTTPException(
                status_code=409,
                detail=detalle_duplicado(campo, repetido),
            )
        raise HTTPException(status_code=500, detail=f"Error al registrar el usuario y su perfil")

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

def actualizar_usuario_por_admin_controller(num_cuenta: str, data, db: Session):
    usuario = db.query(Usuario).filter(Usuario.num_cuenta == num_cuenta).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    try:
        # Actualizamos los campos si vienen incluidos en la petición
        if data.primer_nombre is not None:
            usuario.primer_nombre = data.primer_nombre
        if data.segundo_nombre is not None:
            usuario.segundo_nombre = data.segundo_nombre
        if data.primer_apellido is not None:
            usuario.primer_apellido = data.primer_apellido
        if data.segundo_apellido is not None:
            usuario.segundo_apellido = data.segundo_apellido
        if data.correo_personal is not None:
            usuario.correo_personal = data.correo_personal
        if data.correo_institucional is not None and data.correo_institucional != usuario.correo_institucional:
            correo_existente = db.query(Usuario).filter(
                Usuario.correo_institucional == data.correo_institucional,
                Usuario.num_cuenta != num_cuenta
            ).first()
            if correo_existente:
                raise HTTPException(
                    status_code=400, 
                    detail="El correo institucional ya está registrado por otro usuario"
                )
            usuario.correo_institucional = data.correo_institucional
        if data.telefono is not None:
            usuario.telefono = data.telefono
        if data.carrera_id is not None:
            usuario.carrera_id = data.carrera_id
        if data.rol_id is not None:
            usuario.rol_id = data.rol_id

        db.commit()
        db.refresh(usuario)
        return {"mensaje": f"Usuario con número de cuenta {num_cuenta} actualizado exitosamente"}
    except IntegrityError as e:
        db.rollback()
        print(f"Error de integridad detallado: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Error de integridad en la base de datos"
        )


def asignar_correo_institucional_controller(
    num_cuenta: str,
    data: AsignarCorreoInstitucionalInput,
    db: Session,
):
    """
    Asigna el correo institucional a un usuario que aún no lo tiene
    (o corrige el existente). Las reglas del correo las valida el schema.
    """
    usuario = db.query(Usuario).filter(Usuario.num_cuenta == num_cuenta).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    correo = data.correo_institucional

    if usuario.correo_institucional == correo:
        return {
            "mensaje": f"El correo institucional de {num_cuenta} ya estaba asignado",
            "num_cuenta": usuario.num_cuenta,
            "correo_institucional": correo,
        }

    correo_existente = (
        db.query(Usuario)
        .filter(
            Usuario.correo_institucional == correo,
            Usuario.num_cuenta != num_cuenta,
        )
        .first()
    )
    if correo_existente:
        raise HTTPException(
            status_code=400,
            detail="El correo institucional ya está registrado por otro usuario",
        )

    try:
        usuario.correo_institucional = correo
        db.commit()
        db.refresh(usuario)
    except IntegrityError as e:
        db.rollback()
        print(f"Error de integridad detallado: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Error de integridad en la base de datos",
        )

    return {
        "mensaje": f"Correo institucional asignado a {num_cuenta}",
        "num_cuenta": usuario.num_cuenta,
        "correo_institucional": usuario.correo_institucional,
    }


def consultar_disponibilidad_controller(
    db: Session,
    num_cuenta: Optional[str] = None,
    correo_institucional: Optional[str] = None,
) -> dict:
    """
    Indica si el dato ya pertenece a un usuario registrado.

    Se usa en el alta para avisar mientras el administrador escribe,
    antes de completar el resto del formulario. No devuelve datos
    del registro existente: el detalle con el nombre y el enlace al
    estudiante lo entrega el error 409 al intentar guardar.
    """
    consulta = db.query(Usuario)

    if num_cuenta:
        consulta = consulta.filter(Usuario.num_cuenta == num_cuenta.strip())
    else:
        consulta = consulta.filter(
            Usuario.correo_institucional == correo_institucional.strip().lower()
        )

    return {"disponible": consulta.first() is None}


def contar_referencias(num_cuenta: str, db: Session) -> dict:
    """Cuenta los registros de otras tablas que apuntan al estudiante."""
    return {
        tabla: db.query(modelo).filter(modelo.num_cuenta == num_cuenta).count()
        for modelo, tabla, _ in REFERENCIAS_DEL_ESTUDIANTE
    }


def eliminar_estudiante_controller(num_cuenta: str, db: Session):
    """
    Borra al estudiante y su perfil de becario definitivamente.

    No borra datos históricos: si el estudiante aparece en asistencias,
    aportaciones, multas o pagos, se rechaza indicando cuáles lo usan.
    """
    usuario = db.query(Usuario).filter(Usuario.num_cuenta == num_cuenta).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    referencias = {
        tabla: total
        for tabla, total in contar_referencias(num_cuenta, db).items()
        if total > 0
    }

    if referencias:
        nombres = [
            descripcion
            for _, tabla, descripcion in REFERENCIAS_DEL_ESTUDIANTE
            if tabla in referencias
        ]
        raise HTTPException(
            status_code=409,
            detail={
                "mensaje": (
                    "El estudiante tiene {0} y no puede eliminarse".format(
                        ", ".join(nombres)
                    )
                ),
                "campo": "referencias",
                "num_cuenta": num_cuenta,
                "referencias": referencias,
            },
        )

    try:
        # Los PIN dependen del correo institucional, no de la cuenta.
        if usuario.correo_institucional:
            db.query(PinActivacion).filter(
                PinActivacion.correo == usuario.correo_institucional
            ).delete(synchronize_session=False)
            db.query(PinIntentos).filter(
                PinIntentos.correo == usuario.correo_institucional
            ).delete(synchronize_session=False)

        # El perfil se borra antes porque apunta al usuario.
        perfiles = (
            db.query(Becario)
            .filter(Becario.num_cuenta == num_cuenta)
            .delete(synchronize_session=False)
        )
        db.delete(usuario)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        print(f"Error al eliminar al estudiante {num_cuenta}: {e}")
        raise HTTPException(
            status_code=409,
            detail="El estudiante todavía tiene registros relacionados",
        )

    return {
        "mensaje": f"Estudiante {num_cuenta} eliminado",
        "num_cuenta": num_cuenta,
        "eliminados": {"perfiles_becarios": perfiles},
    }
