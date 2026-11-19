import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from models.aportacion import Aportacion
from models.estado_aportación import EstadoAportacion
from models.becario import Becario


CARPETA_DESTINO = "uploads/aportaciones"

# Carpeta base del proyecto. Las rutas guardadas en la base son relativas
# a ella (uploads/aportaciones/...), sin importar el directorio de trabajo.
DIRECTORIO_PROYECTO = Path(__file__).resolve().parents[1]

# Tipos de comprobante aceptados, mapeados a su tipo MIME y a los tipos
# que el navegador puede reportar para esa misma extensión.
TIPOS_PDF = {
    ".pdf": ("application/pdf", {"application/pdf", "application/x-pdf"}),
}

TIPOS_IMAGEN = {
    ".jpg": ("image/jpeg", {"image/jpeg", "image/jpg", "image/pjpeg"}),
    ".jpeg": ("image/jpeg", {"image/jpeg", "image/jpg", "image/pjpeg"}),
    ".png": ("image/png", {"image/png", "image/x-png"}),
    ".webp": ("image/webp", {"image/webp"}),
}

EXTENSIONES_PDF = tuple(TIPOS_PDF)
EXTENSIONES_IMAGEN = tuple(TIPOS_IMAGEN)
EXTENSIONES_COMPROBANTE = EXTENSIONES_PDF + EXTENSIONES_IMAGEN

TIPOS_MIME_POR_EXTENSION = {
    extension: mime
    for extension, (mime, _) in {**TIPOS_PDF, **TIPOS_IMAGEN}.items()
}


def _validar_comprobante(archivo: UploadFile, tipo_esperado: str) -> str:
    """
    Valida extensión y tipo MIME del archivo y devuelve su extensión.

    Antes esta lógica vivía en la primera línea del controlador y reventaba
    con 500 cuando el navegador no enviaba el nombre del archivo.
    """
    nombre = (archivo.filename or "").strip()
    if not nombre:
        raise HTTPException(
            status_code=400,
            detail="El archivo enviado no tiene un nombre válido",
        )

    extension = os.path.splitext(nombre)[1].lower()
    permitidas = EXTENSIONES_PDF if tipo_esperado == "pdf" else EXTENSIONES_IMAGEN

    if extension not in permitidas:
        esperado = "PDF" if tipo_esperado == "pdf" else "JPG, PNG o WEBP"
        raise HTTPException(
            status_code=400,
            detail=f"El comprobante debe ser un archivo {esperado}",
        )

    tipos = {**TIPOS_PDF, **TIPOS_IMAGEN}
    _, mimes_validos = tipos[extension]
    mime = (archivo.content_type or "").strip().lower()

    # Algunos navegadores envían el tipo vacío; en ese caso se conserva la
    # validación por extensión. Si envían un tipo, debe corresponder.
    if mime and mime not in mimes_validos:
        raise HTTPException(
            status_code=400,
            detail="El tipo del archivo enviado no corresponde a su extensión",
        )

    return extension


def _guardar_comprobante(
    archivo: UploadFile,
    extension: str,
    num_cuenta: str,
    num_referencia: str,
) -> str:
    """Guarda el archivo en la carpeta destino y devuelve su ruta relativa."""
    carpeta = os.path.join(str(DIRECTORIO_PROYECTO), CARPETA_DESTINO)

    try:
        os.makedirs(carpeta, exist_ok=True)
    except OSError as error:
        print(f"No se pudo crear la carpeta de comprobantes: {error}")
        raise HTTPException(
            status_code=500,
            detail="Error al preparar la carpeta de comprobantes en el servidor",
        )

    # El número de referencia lo envía el cliente: se sanea antes de usarlo
    # como parte de un nombre de archivo para evitar rutas arbitrarias.
    nombre_archivo = (
        f"{_sanear_segmento(num_cuenta)}_{_sanear_segmento(num_referencia)}"
        f"_{_sanear_segmento(os.path.basename(archivo.filename or ''))}"
    )
    ruta_relativa = f"{CARPETA_DESTINO}/{nombre_archivo}"
    ruta_absoluta = os.path.join(carpeta, nombre_archivo)

    if not os.path.commonpath([carpeta, os.path.abspath(ruta_absoluta)]) == carpeta:
        raise HTTPException(
            status_code=400,
            detail="El nombre del archivo no es válido",
        )

    try:
        with open(ruta_absoluta, "wb") as buffer:
            shutil.copyfileobj(archivo.file, buffer)
    except OSError as error:
        # No dejar archivos a medias si la copia se cortó.
        if os.path.isfile(ruta_absoluta):
            os.remove(ruta_absoluta)
        print(f"No se pudo guardar el comprobante: {error}")
        raise HTTPException(
            status_code=500,
            detail="Error al guardar el comprobante en el servidor",
        )

    return ruta_relativa


def _sanear_segmento(texto: str) -> str:
    """Quita separadores de ruta y caracteres problemáticos de un nombre."""
    limpio = re.sub(r"[^A-Za-z0-9._-]", "_", (texto or "").strip())
    return limpio.lstrip(".") or "archivo"


def crear_aportacion_controller(
    num_cuenta: str,
    num_referencia: str,
    archivo_pdf: UploadFile | None,
    archivo_imagen: UploadFile | None,
    descripcion: str,
    db: Session,
):
    num_referencia = (num_referencia or "").strip()
    if not num_referencia:
        raise HTTPException(
            status_code=400,
            detail="El número de referencia es obligatorio",
        )

    if not archivo_pdf and not archivo_imagen:
        raise HTTPException(
            status_code=400,
            detail="Debe adjuntar el comprobante en PDF o en imagen",
        )

    extension_pdf = (
        _validar_comprobante(archivo_pdf, "pdf") if archivo_pdf else None
    )
    extension_imagen = (
        _validar_comprobante(archivo_imagen, "imagen") if archivo_imagen else None
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

    rutas_guardadas: list[str] = []
    ruta_pdf: str | None = None
    ruta_imagen: str | None = None
    try:
        if archivo_pdf and extension_pdf:
            ruta_pdf = _guardar_comprobante(
                archivo_pdf, extension_pdf, num_cuenta, num_referencia
            )
            rutas_guardadas.append(ruta_pdf)

        if archivo_imagen and extension_imagen:
            ruta_imagen = _guardar_comprobante(
                archivo_imagen, extension_imagen, num_cuenta, num_referencia
            )
            rutas_guardadas.append(ruta_imagen)

        nueva_aportacion = Aportacion(
            num_cuenta=num_cuenta,
            num_referencia=num_referencia,
            descripcion=descripcion,
            # La columna es obligatoria: si no vino PDF, la imagen hace de
            # comprobante principal y ruta_pdf apunta a ella.
            ruta_pdf=ruta_pdf or ruta_imagen,
            ruta_imagen=ruta_imagen,
            estado_aportacion_id=estado_pendiente.id,
        )

        db.add(nueva_aportacion)
        db.commit()
    except IntegrityError:
        db.rollback()
        _eliminar_archivos(rutas_guardadas)
        raise HTTPException(
            status_code=400,
            detail="El número de referencia ya fue utilizado",
        )
    except HTTPException:
        db.rollback()
        _eliminar_archivos(rutas_guardadas)
        raise
    except SQLAlchemyError as error:
        db.rollback()
        _eliminar_archivos(rutas_guardadas)
        print(f"No se pudo registrar la aportación: {error}")
        raise HTTPException(
            status_code=500,
            detail="Error al registrar la aportación en la base de datos",
        )

    db.refresh(nueva_aportacion)
    return {
        "id": nueva_aportacion.id,
        "num_cuenta": nueva_aportacion.num_cuenta,
        "num_referencia": nueva_aportacion.num_referencia,
        "descripcion": nueva_aportacion.descripcion,
        "ruta_pdf": nueva_aportacion.ruta_pdf,
        "ruta_imagen": nueva_aportacion.ruta_imagen,
        "estado": nueva_aportacion.estado.nombre_estado if nueva_aportacion.estado else "Pendiente",
        "fecha_subida": nueva_aportacion.fecha_subida
    }


def _eliminar_archivos(rutas: list[str]) -> None:
    """Elimina comprobantes ya escritos cuando la aportación no se guardó."""
    for ruta in rutas:
        try:
            os.remove(os.path.join(str(DIRECTORIO_PROYECTO), ruta))
        except OSError:
            pass


MONTO_POR_MES = 20


def obtener_archivo_aportacion_controller(aportacion_id: int, db: Session):
    """
    Devuelve el comprobante PDF de una aportación.

    La ruta guardada en la base es relativa al proyecto
    (uploads/aportaciones/...), así que se resuelve desde la raíz del
    proyecto y se valida que quede dentro de la carpeta permitida antes
    de servirla, para evitar lecturas arbitrarias.
    """
    aportacion = (
        db.query(Aportacion).filter(Aportacion.id == aportacion_id).first()
    )
    if not aportacion:
        raise HTTPException(status_code=404, detail="Aportación no encontrada")

    ruta_registrada = (aportacion.ruta_pdf or "").strip()
    if not ruta_registrada:
        raise HTTPException(
            status_code=404, detail="La aportación no tiene comprobante registrado"
        )

    carpeta = os.path.join(str(DIRECTORIO_PROYECTO), CARPETA_DESTINO)

    # Las rutas guardadas incluyen sus carpetas (uploads/aportaciones/x.pdf),
    # así que se resuelven completas desde la raíz del proyecto. Si la fila
    # guardó solo el nombre del archivo, se antepone la carpeta destino.
    if os.path.isabs(ruta_registrada):
        ruta_absoluta = os.path.abspath(ruta_registrada)
    elif os.path.dirname(ruta_registrada):
        ruta_absoluta = os.path.abspath(
            os.path.join(str(DIRECTORIO_PROYECTO), ruta_registrada)
        )
    else:
        ruta_absoluta = os.path.abspath(
            os.path.join(carpeta, ruta_registrada)
        )

    # Nunca servir archivos fuera del directorio de aportaciones.
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
        media_type=TIPOS_MIME_POR_EXTENSION.get(
            os.path.splitext(ruta_absoluta)[1].lower(), "application/octet-stream"
        ),
        filename=os.path.basename(ruta_absoluta),
    )


def revisar_aportacion_controller(
    aportacion_id: int,
    nombre_estado: str,
    meses_aprobados: int | None,
    comentario: str | None,
    db: Session,
):
    # 1. Validar el estado destino ANTES de tocar la aportación
    estado_obj = (
        db.query(EstadoAportacion)
        .filter(EstadoAportacion.nombre_estado == nombre_estado)
        .first()
    )
    if not estado_obj:
        raise HTTPException(
            status_code=400,
            detail=f"El estado '{nombre_estado}' no es válido",
        )

    aportacion = db.query(Aportacion).filter(Aportacion.id == aportacion_id).first()
    if not aportacion:
        raise HTTPException(status_code=404, detail="Aportación no encontrada")

    # 2. Guardar el estado actual ANTES de modificarlo (para revertir montos)
    estado_anterior = aportacion.estado.nombre_estado if aportacion.estado else None
    meses_anteriores = aportacion.meses_aprobados or 0

    comentario = (comentario or "").strip()

    # 3. Reglas de negocio según el estado destino
    if nombre_estado in ("Aprobado", "Rechazado") and not comentario:
        # La justificación es obligatoria tanto al aprobar como al rechazar.
        raise HTTPException(
            status_code=400,
            detail="Debe indicar la justificación de la decisión",
        )

    if nombre_estado == "Aprobado":
        if not meses_aprobados or meses_aprobados <= 0:
            raise HTTPException(
                status_code=400,
                detail="Debe especificar una cantidad válida de meses",
            )
        nuevo_meses = meses_aprobados
    elif nombre_estado == "Rechazado":
        nuevo_meses = 0
    else:  # Pendiente
        nuevo_meses = 0

    # 4. Ajustar el monto acumulado del becario con el delta real
    usuario = (
        db.query(Becario)
        .filter(Becario.num_cuenta == aportacion.num_cuenta)
        .first()
    )
    if usuario:
        meses_previos_que_contaban = (
            meses_anteriores if estado_anterior == "Aprobado" else 0
        )
        meses_nuevos_que_cuentan = nuevo_meses if nombre_estado == "Aprobado" else 0
        delta = (meses_nuevos_que_cuentan - meses_previos_que_contaban) * MONTO_POR_MES
        if delta:
            usuario.monto_acumulado = max(0, (usuario.monto_acumulado or 0) + delta)

    # 5. Persistir cambios en la aportación
    aportacion.estado_aportacion_id = estado_obj.id
    aportacion.meses_aprobados = nuevo_meses
    aportacion.comentario = comentario or None

    db.commit()
    db.refresh(aportacion)

    return {
        "mensaje": f"Aportación actualizada a '{nombre_estado}' exitosamente",
        "id": aportacion.id,
        "estado": nombre_estado,
        "meses_aprobados": aportacion.meses_aprobados,
        "comentario": aportacion.comentario,
    }

def mis_aportaciones_controller(num_cuenta: str, db:Session):
    aportaciones = db.query(Aportacion).filter(Aportacion.num_cuenta == num_cuenta).all()

    return [
        {
            "id": a.id,
            "num_cuenta": a.num_cuenta,
            "num_referencia": a.num_referencia,
            "descripcion": a.descripcion,
            "ruta_pdf": a.ruta_pdf,
            "ruta_imagen": a.ruta_imagen,
            "estado": a.estado.nombre_estado if a.estado else "Desconocido",
            "meses_aprobados": a.meses_aprobados,
            "fecha_subida": a.fecha_subida,
            "comentario": a.comentario
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
            "ruta_imagen": a.ruta_imagen,
            "estado": a.estado.nombre_estado if a.estado else "Desconocido",
            "fecha_subida": a.fecha_subida,
            "comentario": a.comentario
        }
        for a in aportaciones
    ]
