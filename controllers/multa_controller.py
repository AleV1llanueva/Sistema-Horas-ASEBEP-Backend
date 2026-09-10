import os
import shutil
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from models.multa import Multa
from models.asistencia import Asistencia
from models.usuario import Usuario
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
    multas = db.query(Multa).all()

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

