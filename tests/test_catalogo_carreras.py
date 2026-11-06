"""
Pruebas del catálogo de carreras que usa el alta de estudiantes.

El frontend pide `/carreras/catalogo`; si la ruta no existiera, FastAPI la
interpretaría como `/carreras/{carrera_id}` y respondería 422.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import autorizacion
from models import Carrera
from routes.carrera import router as carrera_router
from utils.database import get_db

ADMIN = autorizacion("Admin General", "20209999999")


@pytest.fixture
def cliente_carreras(db):
    app = FastAPI()
    app.include_router(carrera_router)
    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app) as cliente_prueba:
        yield cliente_prueba


def test_catalogo_devuelve_solo_carreras_activas(cliente_carreras, db):
    activa = Carrera(nombre_carrera="Ingeniería en Sistemas", activo=True)
    inactiva = Carrera(nombre_carrera="Carrera Retirada", activo=False)
    db.add_all([activa, inactiva])
    db.commit()

    respuesta = cliente_carreras.get("/carreras/catalogo", headers=ADMIN)

    assert respuesta.status_code == 200, respuesta.text
    carreras = respuesta.json()
    assert [carrera["nombre_carrera"] for carrera in carreras] == [
        "Ingeniería en Sistemas"
    ]
    assert carreras[0]["id"] == activa.id
    assert carreras[0]["activo"] is True
