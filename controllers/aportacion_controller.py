import os
import shutil
from datetime import datetime
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from models.aportacion import Aportacion
from models.estado_aportación import EstadoAportacion
from models.becario import Becario


CARPETA_DESTINO = "uploads/aportaciones"

def crear_aportacion_controller(num_cuenta: str, num_referencia: str, archivo_pdf: UploadFile, descripcion: str,db:Session):
    if not archivo_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, 
            details=f"El archivo debe ser formato PDF válido"
            )
    existente = db.query(Aportacion).filter(Aportacion.num_referencia == num_referencia).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail="El número de referencia ya fue utilizado"
        )

    estado_pendiente = db.query(EstadoAportacion).filter(EstadoAportacion.nombre_estado == "Pendiente").first()
    if not estado_pendiente:
        raise HTTPException(
            status_code=500,
            detail="El estado pendiente no está configurado en la base de datos"
        )

    os.makedirs(CARPETA_DESTINO, exist_ok=True)
    nombre_archivo = f"{num_cuenta}_{num_referencia}_{archivo_pdf.filename}"
    ruta_archivo = os.path.join(CARPETA_DESTINO, nombre_archivo)

    try:
        with open(ruta_archivo, "wb") as buffer:
            shutil.copyfileobj(archivo_pdf.file, buffer)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error al guardar el archivo pdf en el servidor"
        )

    nueva_aportacion = Aportacion(
        num_cuenta=num_cuenta,
        num_referencia=num_referencia,
        descripcion=descripcion,
        ruta_pdf=ruta_archivo,
        estado_aportacion_id=estado_pendiente.id
    )

    db.add(nueva_aportacion)
    db.commit()
    db.refresh(nueva_aportacion)
    return {
        "id": nueva_aportacion.id,
        "num_cuenta": nueva_aportacion.num_cuenta,
        "num_referencia": nueva_aportacion.num_referencia,
        "descripcion": nueva_aportacion.descripcion,
        "ruta_pdf": nueva_aportacion.ruta_pdf,
        "estado": nueva_aportacion.estado.nombre_estado if nueva_aportacion.estado else "Pendiente",
        "fecha_subida": nueva_aportacion.fecha_subida
    }


def revisar_aportacion_controller(aportacion_id:int, nombre_estado:str,meses_aprobados: int | None, db:Session):
    estado_obj = db.query(EstadoAportacion).filter(EstadoAportacion.nombre_estado == nombre_estado).first()
    if not estado_obj:
        raise HTTPException(
            status_code=400,
            detail=f"El estado '{nombre_estado}' no es válido"
        )

    aportacion = db.query(Aportacion).filter(Aportacion.id == aportacion_id).first()
    if not aportacion:
        raise HTTPException(
            status_code=404,
            detail="Aportacion no encontrada"
        )

    aportacion.estado_aportacion_id=estado_obj.id
    if nombre_estado == "Aprobado":
        if not meses_aprobados or meses_aprobados <= 0:
            raise HTTPException(
                status_code=400,
                detail="Debe especificar una cantidad válida de meses"
            )
        aportacion.meses_aprobados = meses_aprobados
        usuario = db.query(Becario).filter(Becario.num_cuenta == aportacion.num_cuenta).first()
        if usuario:
            monto = 20
            usuario.monto_acumulado += (monto * meses_aprobados)
    db.commit()
    return {"mensaje": f"Aportación actualizada a {nombre_estado} por {meses_aprobados} mes(es) exitosamente"}

def mis_aportaciones_controller(num_cuenta: str, db:Session):
    aportaciones = db.query(Aportacion).filter(Aportacion.num_cuenta == num_cuenta).all()

    return [
        {
            "id": a.id,
            "num_cuenta": a.num_cuenta,
            "num_referencia": a.num_referencia,
            "descripcion": a.descripcion,
            "ruta_pdf": a.ruta_pdf,
            "estado": a.estado.nombre_estado if a.estado else "Desconocido",
            "meses_aprobados": a.meses_aprobados,
            "fecha_subida": a.fecha_subida

        }
        for a in aportaciones
    ]

def listar_aportaciones_pendientes_controller(db: Session):

    aportaciones = db.query(Aportacion).all()
    
    return [
        {
            "id": a.id,
            "num_cuenta": a.num_cuenta,
            "num_referencia": a.num_referencia,
            "descripcion": a.descripcion,
            "ruta_pdf": a.ruta_pdf,
            "estado": a.estado.nombre_estado if a.estado else "Desconocido",
            "fecha_subida": a.fecha_subida
        }
        for a in aportaciones
    ]
