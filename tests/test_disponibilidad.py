"""
Pruebas de la comprobación previa de datos en el alta de estudiantes.

El administrador necesita saber, mientras escribe, si el número de
cuenta o el correo institucional ya pertenecen a un estudiante. La
respuesta no expone datos personales.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import autorizacion
from models import Usuario
from routes.usuario import router as usuario_router
from utils.database import get_db

CUENTA = "20211000001"


def _cliente(db):
    app = FastAPI()
    app.include_router(usuario_router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def _usuario(db):
    db.add(
        Usuario(
            num_cuenta=CUENTA,
            primer_nombre="Ana",
            primer_apellido="López",
            correo_institucional="ana.lopez@unah.hn",
            active=False,
        )
    )
    db.commit()


def test_cuenta_existente_se_informa(db):
    _usuario(db)

    respuesta = _cliente(db).get(
        "/usuarios/disponibilidad",
        params={"num_cuenta": CUENTA},
        headers=autorizacion("Admin General", "20209999999"),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"disponible": False}


def test_correo_existente_se_informa_sin_importar_mayusculas(db):
    _usuario(db)

    respuesta = _cliente(db).get(
        "/usuarios/disponibilidad",
        params={"correo_institucional": "ANA.LOPEZ@UNAH.HN"},
        headers=autorizacion("Admin General", "20209999999"),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"disponible": False}


def test_dato_libre_se_informa_disponible(db):
    _usuario(db)

    respuesta = _cliente(db).get(
        "/usuarios/disponibilidad",
        params={"num_cuenta": "20211099999"},
        headers=autorizacion("Admin General", "20209999999"),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"disponible": True}


def test_comprobacion_exige_autenticacion(db):
    respuesta = _cliente(db).get(
        "/usuarios/disponibilidad",
        params={"num_cuenta": CUENTA},
    )

    assert respuesta.status_code in (401, 400), respuesta.text
