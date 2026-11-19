"""
Pruebas de la creación de aportaciones con comprobante PDF o imagen.

Se prueban los casos que antes terminaban en 500 (nombre de archivo ausente,
ruta con separadores, commit fallido) y la subida de una imagen sola.
"""

import io
from pathlib import Path

import pytest

import controllers.aportacion_controller as controlador
from controllers.aportacion_controller import crear_aportacion_controller
from fastapi import HTTPException, UploadFile
from models import Aportacion, EstadoAportacion


@pytest.fixture
def carpeta_temporal(tmp_path, monkeypatch):
    """Redirige los comprobantes a una carpeta temporal."""
    monkeypatch.setattr(controlador, "DIRECTORIO_PROYECTO", tmp_path)
    return tmp_path / controlador.CARPETA_DESTINO


@pytest.fixture
def estado_pendiente(db):
    estado = EstadoAportacion(nombre_estado="Pendiente")
    db.add(estado)
    db.commit()
    return estado


def _archivo(nombre, contenido, tipo):
    return UploadFile(
        filename=nombre,
        file=io.BytesIO(contenido),
        headers={"content-type": tipo},
    )


def test_imagen_sola_crea_la_aportacion(db, estado_pendiente, carpeta_temporal):
    resultado = crear_aportacion_controller(
        num_cuenta="20211000001",
        num_referencia="AP-IMG-001",
        archivo_pdf=None,
        archivo_imagen=_archivo("captura.png", b"\x89PNG dato", "image/png"),
        descripcion="Pago por transferencia",
        db=db,
    )

    assert resultado["estado"] == "Pendiente"
    assert resultado["ruta_imagen"].endswith("captura.png")
    assert resultado["ruta_pdf"] == resultado["ruta_imagen"]
    assert (carpeta_temporal / "20211000001_AP-IMG-001_captura.png").is_file()


def test_pdf_e_imagen_se_guardan_por_separado(db, estado_pendiente, carpeta_temporal):
    resultado = crear_aportacion_controller(
        num_cuenta="20211000002",
        num_referencia="AP-MIX-001",
        archivo_pdf=_archivo("comprobante.pdf", b"%PDF dato", "application/pdf"),
        archivo_imagen=_archivo("foto.jpg", b"\xff\xd8 dato", "image/jpeg"),
        descripcion="Pago con ambos comprobantes",
        db=db,
    )

    assert resultado["ruta_pdf"].endswith("comprobante.pdf")
    assert resultado["ruta_imagen"].endswith("foto.jpg")
    assert (carpeta_temporal / "20211000002_AP-MIX-001_comprobante.pdf").is_file()
    assert (carpeta_temporal / "20211000002_AP-MIX-001_foto.jpg").is_file()


def test_sin_comprobante_devuelve_400(db, estado_pendiente, carpeta_temporal):
    with pytest.raises(HTTPException) as error:
        crear_aportacion_controller(
            num_cuenta="20211000003",
            num_referencia="AP-000",
            archivo_pdf=None,
            archivo_imagen=None,
            descripcion="Sin archivo",
            db=db,
        )

    assert error.value.status_code == 400


def test_nombre_ausente_devuelve_400_y_no_500(db, estado_pendiente, carpeta_temporal):
    archivo = UploadFile(filename="", file=io.BytesIO(b"%PDF dato"))

    with pytest.raises(HTTPException) as error:
        crear_aportacion_controller(
            num_cuenta="20211000004",
            num_referencia="AP-001",
            archivo_pdf=archivo,
            archivo_imagen=None,
            descripcion="Nombre ausente",
            db=db,
        )

    assert error.value.status_code == 400


def test_extension_no_permitida_devuelve_400(db, estado_pendiente, carpeta_temporal):
    with pytest.raises(HTTPException) as error:
        crear_aportacion_controller(
            num_cuenta="20211000005",
            num_referencia="AP-002",
            archivo_pdf=None,
            archivo_imagen=_archivo("nota.txt", b"texto", "text/plain"),
            descripcion="Archivo no permitido",
            db=db,
        )

    assert error.value.status_code == 400


def test_referencia_con_separadores_no_escapa_de_la_carpeta(
    db, estado_pendiente, carpeta_temporal
):
    resultado = crear_aportacion_controller(
        num_cuenta="20211000006",
        num_referencia="../../fuera",
        archivo_pdf=_archivo("comprobante.pdf", b"%PDF dato", "application/pdf"),
        archivo_imagen=None,
        descripcion="Intento de ruta",
        db=db,
    )

    archivo_guardado = Path(resultado["ruta_pdf"])
    assert ".." not in archivo_guardado.parts
    assert list(carpeta_temporal.iterdir())


def test_referencia_duplicada_devuelve_400(db, estado_pendiente, carpeta_temporal):
    argumentos = {
        "num_cuenta": "20211000007",
        "num_referencia": "AP-DUP",
        "archivo_pdf": None,
        "archivo_imagen": _archivo("captura.png", b"\x89PNG dato", "image/png"),
        "descripcion": "Primera",
        "db": db,
    }
    crear_aportacion_controller(**argumentos)

    with pytest.raises(HTTPException) as error:
        crear_aportacion_controller(
            **{
                **argumentos,
                "archivo_imagen": _archivo("captura.png", b"\x89PNG dato", "image/png"),
            }
        )

    assert error.value.status_code == 400
    assert db.query(Aportacion).count() == 1
