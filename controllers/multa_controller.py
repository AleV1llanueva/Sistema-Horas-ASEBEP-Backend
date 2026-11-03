import os
import shutil
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.multa import Multa
from models.asistencia import Asistencia
from models.usuario import Usuario
from models.actividad import Actividad
from models.comprobantes_multa import ComprobanteMulta
from models.estado_aportación import EstadoAportacion
from schemas.multa import RegistrarMultaInput, MultaResponse


UPLOAD_DIR = "uploads/multas"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def registrar_multa_controller(data: RegistrarMultaInput, db: Session) -> MultaResponse:
    #Verificar que el usuario existe
    usuario = db.query(Usuario).filter(
        Usuario.num_cuenta == data.num_cuenta
    ).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    #Verificar que el becario estaba inscrito en la actividad
    inscripcion = db.query(Asistencia).filter(
        Asistencia.actividad_id == data.actividad_id,
        Asistencia.num_cuenta == data.num_cuenta
    ).first()
    if not inscripcion:
        raise HTTPException(status_code=400, detail="El becario no estaba inscrito en esta actividad")

    #Verificar que no tenga ya una multa por esta actividad
    multa_existente = db.query(Multa).filter(
        Multa.num_cuenta == data.num_cuenta,
        Multa.actividad_id == data.actividad_id
    ).first()
    if multa_existente:
        raise HTTPException(status_code=400, detail="Ya existe una multa para este becario en esta actividad")

    #Registrar multa
    nueva_multa = Multa(
        num_cuenta=data.num_cuenta,
        actividad_id=data.actividad_id,
        motivo=data.motivo,
        monto=data.monto
    )
    db.add(nueva_multa)
    db.commit()
    db.refresh(nueva_multa)

    return MultaResponse(
        id=nueva_multa.id,
        num_cuenta=nueva_multa.num_cuenta,
        actividad_id=nueva_multa.actividad_id,
        motivo=nueva_multa.motivo,
        monto=nueva_multa.monto,
        pagada=nueva_multa.pagada,
        fecha_multa=nueva_multa.fecha_multa
    )


def ver_inscritos_para_multa_controller(actividad_id: int, db: Session):
    """
    Inscritos de una actividad para registrar multas.

    Incluye el nombre del estudiante y si ya tiene multa en esa
    actividad, para que el administrador no intente duplicarla
    (el endpoint de registro lo rechazaría con 400).
    """
    actividad = (
        db.query(Actividad).filter(Actividad.id == actividad_id).first()
    )
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    filas = (
        db.query(Asistencia, Usuario, Multa)
        .outerjoin(Usuario, Usuario.num_cuenta == Asistencia.num_cuenta)
        .outerjoin(
            Multa,
            and_(
                Multa.num_cuenta == Asistencia.num_cuenta,
                Multa.actividad_id == actividad_id,
            ),
        )
        .filter(Asistencia.actividad_id == actividad_id)
        .all()
    )

    inscritos = []

    for asistencia, usuario, multa in filas:
        nombre = None
        if usuario:
            nombre = " ".join(
                parte
                for parte in [
                    usuario.primer_nombre,
                    usuario.segundo_nombre,
                    usuario.primer_apellido,
                    usuario.segundo_apellido,
                ]
                if parte
            )

        inscritos.append(
            {
                "num_cuenta": asistencia.num_cuenta,
                "nombre_estudiante": nombre,
                "check_in": bool(asistencia.check_in),
                "check_out": bool(asistencia.check_out),
                "estado": (
                    asistencia.estado.nombre_estado
                    if asistencia.estado
                    else "Sin estado"
                ),
                "multa_registrada": multa is not None,
            }
        )

    return {
        "actividad_id": actividad.id,
        "titulo": actividad.titulo,
        "fecha_actividad": actividad.fecha_actividad,
        "inscritos": inscritos,
    }


def ver_multas_becario_controller(num_cuenta: str, db: Session):
    multas = db.query(Multa).filter(
        Multa.num_cuenta == num_cuenta
    ).all()

    return [
        MultaResponse(
            id=m.id,
            num_cuenta=m.num_cuenta,
            actividad_id=m.actividad_id,
            motivo=m.motivo,
            monto=m.monto,
            pagada=m.pagada,
            fecha_multa=m.fecha_multa
        )
        for m in multas
    ]


def ver_todas_multas_controller(db: Session):
    """
    Lista todas las multas con el nombre del estudiante y el título
    de la actividad, para que el panel administrativo no tenga que
    cruzar datos en el cliente.
    """
    filas = (
        db.query(Multa, Usuario, Actividad)
        .outerjoin(Usuario, Usuario.num_cuenta == Multa.num_cuenta)
        .outerjoin(Actividad, Actividad.id == Multa.actividad_id)
        .order_by(Multa.fecha_multa.desc())
        .all()
    )

    return [
        {
            "id": m.id,
            "num_cuenta": m.num_cuenta,
            "actividad_id": m.actividad_id,
            "motivo": m.motivo,
            "monto": m.monto,
            "pagada": m.pagada,
            "fecha_multa": m.fecha_multa,
            "nombre_estudiante": (
                " ".join(
                    parte
                    for parte in [
                        usuario.primer_nombre,
                        usuario.segundo_nombre,
                        usuario.primer_apellido,
                        usuario.segundo_apellido,
                    ]
                    if parte
                )
                if usuario
                else None
            ),
            "titulo_actividad": actividad.titulo if actividad else None,
        }
        for m, usuario, actividad in filas
    ]

def enviar_pago_multa_controller(multa_id: int, num_cuenta: str, num_referencia: str, archivo_pdf: UploadFile, db: Session):
    # 1. Verificar que la multa exista y pertenezca al usuario
    multa = db.query(Multa).filter(Multa.id == multa_id, Multa.num_cuenta == num_cuenta).first()
    if not multa:
        raise HTTPException(status_code=404, detail="Multa no encontrada o no pertenece al usuario")
    
    if multa.pagada:
        raise HTTPException(status_code=400, detail="Esta multa ya se encuentra pagada")

    # 2. Guardar el archivo PDF del comprobante
    file_path = os.path.join(UPLOAD_DIR, f"{num_cuenta}_{multa_id}_{archivo_pdf.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(archivo_pdf.file, buffer)

    # 3. Buscar el estado "Pendiente"
    estado_pendiente = db.query(EstadoAportacion).filter(EstadoAportacion.nombre_estado == "Pendiente").first()
    if not estado_pendiente:
        raise HTTPException(status_code=500, detail="No se encontró el estado 'Pendiente' en el sistema")

    # 4. Crear el registro del comprobante
    nuevo_comprobante = ComprobanteMulta(
        multa_id=multa_id,
        num_cuenta=num_cuenta,
        num_referencia=num_referencia,
        ruta_pdf=file_path,
        estado_id=estado_pendiente.id
    )
    db.add(nuevo_comprobante)
    db.commit()
    db.refresh(nuevo_comprobante)

    return {"mensaje": "Comprobante de multa enviado exitosamente", "comprobante_id": nuevo_comprobante.id}


def revisar_pago_multa_controller(comprobante_id: int, nombre_estado: str, db: Session):
    # 1. Buscar el comprobante
    comprobante = db.query(ComprobanteMulta).filter(ComprobanteMulta.id == comprobante_id).first()
    if not comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    # 2. Buscar el estado destino (ej. "Aprobado" o "Rechazado")
    estado_destino = db.query(EstadoAportacion).filter(EstadoAportacion.nombre_estado == nombre_estado).first()
    if not estado_destino:
        raise HTTPException(status_code=400, detail=f"El estado '{nombre_estado}' no es válido")

    comprobante.estado_id = estado_destino.id

    # 3. Si es Aprobado, marcamos la multa original como pagada
    if nombre_estado == "Aprobado":
        multa = db.query(Multa).filter(Multa.id == comprobante.multa_id).first()
        if multa:
            multa.pagada = True

    db.commit()
    return {"mensaje": f"Pago de multa actualizado a estado: {nombre_estado}"}


def ver_todos_comprobantes_multas_controller(db: Session):
    comprobantes = db.query(ComprobanteMulta).all()
    
    return [
        {
            "id": c.id,
            "multa_id": c.multa_id,
            "num_cuenta": c.num_cuenta,
            "num_referencia": c.num_referencia,
            "ruta_pdf": c.ruta_pdf,
            "estado": c.estado.nombre_estado if c.estado else "Desconocido",
            "fecha_solicitud": c.fecha_solicitud
        }
        for c in comprobantes
    ]


def obtener_archivo_comprobante_multa_controller(comprobante_id: int, db: Session):
    """
    Devuelve el PDF del comprobante de pago de una multa.

    Se valida que la ruta quede dentro de `uploads/multas` para evitar
    que un registro manipulado sirva archivos ajenos.
    """
    comprobante = (
        db.query(ComprobanteMulta)
        .filter(ComprobanteMulta.id == comprobante_id)
        .first()
    )
    if not comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    ruta_registrada = (comprobante.ruta_pdf or "").strip()
    if not ruta_registrada:
        raise HTTPException(
            status_code=404, detail="El comprobante no tiene archivo registrado"
        )

    carpeta = os.path.abspath(UPLOAD_DIR)
    ruta_absoluta = os.path.abspath(ruta_registrada)

    if not os.path.isabs(ruta_registrada):
        ruta_absoluta = os.path.abspath(
            os.path.join(carpeta, os.path.basename(ruta_registrada))
        )

    if os.path.commonpath([carpeta, ruta_absoluta]) != carpeta:
        raise HTTPException(
            status_code=400, detail="La ruta del comprobante no es válida"
        )

    if not os.path.isfile(ruta_absoluta):
        raise HTTPException(
            status_code=404, detail="El archivo del comprobante no se encontró"
        )

    return FileResponse(
        path=ruta_absoluta,
        media_type="application/pdf",
        filename=os.path.basename(ruta_absoluta),
    )


def ver_mis_comprobantes_multas_controller(num_cuenta: str, db: Session):
    comprobantes = db.query(ComprobanteMulta).filter(ComprobanteMulta.num_cuenta == num_cuenta).all()
    
    return [
        {
            "id": c.id,
            "multa_id": c.multa_id,
            "num_referencia": c.num_referencia,
            "ruta_pdf": c.ruta_pdf,
            "estado": c.estado.nombre_estado if c.estado else "Desconocido",
            "fecha_solicitud": c.fecha_solicitud
        }
        for c in comprobantes
    ]

