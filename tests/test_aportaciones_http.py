"""
Pruebas de contrato HTTP de las rutas de aportaciones.

Complementan `test_crear_aportacion.py` (que prueba el controlador): aquí se
verifica qué devuelve FastAPI por HTTP.

Contexto: Contributions.jsx muestra
"El servidor no devolvió una respuesta JSON..." cuando la respuesta no tiene
content-type JSON. FastAPI sí responde JSON en 404/405/401, así que esa
pantalla solo aparece cuando la respuesta NO viene de FastAPI manejando la
petición, o cuando el endpoint falla sin manejar (500 en texto plano).
"""

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import controllers.aportacion_controller as controlador
import models  # noqa: F401  (registra todas las tablas)
from core.security import crear_token
from models import Aportacion, Becario, EstadoAportacion
from routes.aportacion import router as aportacion_router
from utils.database import Base, get_db

CUENTA = "20211000001"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    Sesion = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    sesion = Sesion()
    try:
        yield sesion
    finally:
        sesion.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def cliente(db, tmp_path, monkeypatch):
    monkeypatch.setattr(controlador, "DIRECTORIO_PROYECTO", tmp_path)

    app = FastAPI()
    app.include_router(aportacion_router)
    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app, raise_server_exceptions=False) as cliente_prueba:
        yield cliente_prueba


def cabecera(rol="Becario", num_cuenta=CUENTA):
    token = crear_token(
        correo=f"{num_cuenta}@unah.hn",
        rol=rol,
        num_cuenta=num_cuenta,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def estado_pendiente(db):
    estado = EstadoAportacion(nombre_estado="Pendiente")
    db.add(estado)
    db.commit()
    return estado


def _aportacion(db, estado, referencia, cuenta=CUENTA):
    aportacion = Aportacion(
        num_cuenta=cuenta,
        num_referencia=referencia,
        descripcion="pago",
        ruta_pdf=f"{controlador.CARPETA_DESTINO}/{referencia}.pdf",
        estado_aportacion_id=estado.id,
    )
    db.add(aportacion)
    db.commit()
    return aportacion


def test_metodo_no_permitido_responde_json_405(cliente):
    respuesta = cliente.get(
        "/aportaciones/1", headers=cabecera("Admin Aportaciones")
    )

    assert respuesta.status_code == 405
    assert "application/json" in respuesta.headers["content-type"]
    assert respuesta.json()["detail"]


def test_ruta_inexistente_responde_json_404(cliente):
    respuesta = cliente.get("/ruta-inexistente", headers=cabecera())

    assert respuesta.status_code == 404
    assert "application/json" in respuesta.headers["content-type"]


def test_token_invalido_responde_json_401(cliente):
    respuesta = cliente.get(
        "/becario/aportaciones",
        headers={"Authorization": "Bearer token-invalido"},
    )

    assert respuesta.status_code == 401
    assert "application/json" in respuesta.headers["content-type"]


def test_sin_permiso_responde_json_403(cliente):
    respuesta = cliente.get(
        "/becario/aportaciones", headers=cabecera("Admin General")
    )

    assert respuesta.status_code == 403
    assert "application/json" in respuesta.headers["content-type"]


def test_mis_aportaciones_responde_json_200(db, cliente, estado_pendiente):
    _aportacion(db, estado_pendiente, "AP-001")

    respuesta = cliente.get("/becario/aportaciones", headers=cabecera())

    assert respuesta.status_code == 200
    assert "application/json" in respuesta.headers["content-type"]


def test_mis_aportaciones_solo_devuelve_las_de_la_sesion(
    db, cliente, estado_pendiente
):
    _aportacion(db, estado_pendiente, "AP-MIA")
    _aportacion(db, estado_pendiente, "AP-AJENA", cuenta="20211000002")

    respuesta = cliente.get("/becario/aportaciones", headers=cabecera())

    referencias = [fila["num_referencia"] for fila in respuesta.json()]
    assert referencias == ["AP-MIA"]
    assert all(fila["num_cuenta"] == CUENTA for fila in respuesta.json())


def test_post_con_referencia_duplicada_responde_json_400(
    db, cliente, estado_pendiente
):
    _aportacion(db, estado_pendiente, "AP-DUP")

    respuesta = cliente.post(
        "/aportaciones",
        headers=cabecera(),
        data={"num_referencia": "AP-DUP", "descripcion": "repetida"},
        files={
            "archivo_pdf": (
                "comprobante.pdf",
                io.BytesIO(b"%PDF dato"),
                "application/pdf",
            )
        },
    )

    assert respuesta.status_code == 400
    assert "application/json" in respuesta.headers["content-type"]
    assert respuesta.json()["detail"] == "El número de referencia ya fue utilizado"


def test_post_sin_estado_pendiente_en_la_base_responde_json_500(cliente):
    """
    El estado "Pendiente" es obligatorio. Si falta, el controlador lanza 500
    con detail legible, y apiFetch lo muestra tal cual (no el mensaje de JSON).
    """
    respuesta = cliente.post(
        "/aportaciones",
        headers=cabecera(),
        data={"num_referencia": "AP-SIN-ESTADO", "descripcion": "pago"},
        files={
            "archivo_imagen": (
                "captura.png",
                io.BytesIO(b"\x89PNG dato"),
                "image/png",
            )
        },
    )

    assert respuesta.status_code == 500
    assert "application/json" in respuesta.headers["content-type"]
    assert "estado pendiente" in respuesta.json()["detail"].lower()


def test_post_exitoso_devuelve_json_con_todos_los_campos(
    cliente, estado_pendiente
):
    respuesta = cliente.post(
        "/aportaciones",
        headers=cabecera(),
        data={"num_referencia": "AP-OK", "descripcion": "pago"},
        files={
            "archivo_imagen": (
                "captura.png",
                io.BytesIO(b"\x89PNG dato"),
                "image/png",
            )
        },
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "Pendiente"
    assert cuerpo["num_cuenta"] == CUENTA
    assert cuerpo["ruta_pdf"] == cuerpo["ruta_imagen"]


def test_revision_aprobada_suma_monto_al_becario(db, cliente, estado_pendiente):
    aprobado = EstadoAportacion(nombre_estado="Aprobado")
    db.add(aprobado)
    db.add(Becario(num_cuenta=CUENTA, monto_acumulado=0))
    aportacion = _aportacion(db, estado_pendiente, "AP-REV")
    db.commit()

    respuesta = cliente.put(
        f"/aportaciones/{aportacion.id}",
        headers=cabecera("Admin Aportaciones"),
        json={
            "estado": "Aprobado",
            "meses_aprobados": 2,
            "comentario": "Comprobante correcto",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["meses_aprobados"] == 2

    db.expire_all()
    becario = db.query(Becario).filter(Becario.num_cuenta == CUENTA).first()
    assert becario.monto_acumulado == 2 * controlador.MONTO_POR_MES


def test_revision_sin_comentario_responde_json_400(
    db, cliente, estado_pendiente
):
    aprobado = EstadoAportacion(nombre_estado="Aprobado")
    db.add(aprobado)
    aportacion = _aportacion(db, estado_pendiente, "AP-SIN-COMENTARIO")
    db.commit()

    respuesta = cliente.put(
        f"/aportaciones/{aportacion.id}",
        headers=cabecera("Admin Aportaciones"),
        json={"estado": "Aprobado", "meses_aprobados": 1, "comentario": "  "},
    )

    assert respuesta.status_code == 400
    assert "application/json" in respuesta.headers["content-type"]
    assert "justificación" in respuesta.json()["detail"]
