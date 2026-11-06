"""
Pruebas del inicio de sesión.

Una cuenta sin activar debe poder distinguirse de una contraseña
incorrecta: el frontend la envía a activar la cuenta en lugar de
mostrar "credenciales inválidas".
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import autorizacion  # noqa: F401  (asegura las variables de entorno)
from core.security import hashear_password
from models import Becario, Carrera, EstadoBeca, Rol, Usuario
from routes.auth import router as auth_router
from utils.database import get_db

CUENTA = "20211000001"
CONTRASENA = "Secreta2026"


def _preparar_usuario(db, activo, con_password=True):
    rol = Rol(nombre_rol="Becario")
    carrera = Carrera(nombre_carrera="Ingeniería en Sistemas")
    estado = EstadoBeca(nombre_estado="Activo")
    db.add_all([rol, carrera, estado])
    db.commit()

    db.add(
        Usuario(
            num_cuenta=CUENTA,
            primer_nombre="Ana",
            primer_apellido="López",
            correo_institucional="ana.lopez@unah.hn",
            carrera_id=carrera.id,
            rol_id=rol.id,
            active=activo,
            password_hash=hashear_password(CONTRASENA) if con_password else None,
        )
    )
    db.add(
        Becario(
            num_cuenta=CUENTA,
            periodo_inicio="I-PAC",
            anio_inicio=2024,
            mes_inicio=3,
            horas_acumuladas=0,
            monto_acumulado=0,
            estado_beca_id=estado.id,
        )
    )
    db.commit()


def _cliente(db):
    app = FastAPI()
    app.include_router(auth_router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def _login(db, contrasena=CONTRASENA):
    return _cliente(db).post(
        "/auth/login",
        json={"num_cuenta": CUENTA, "password": contrasena},
    )


def test_login_cuenta_inactiva_indica_que_hay_que_activarla(db):
    _preparar_usuario(db, activo=False, con_password=False)

    respuesta = _login(db)

    assert respuesta.status_code == 403, respuesta.text
    detalle = respuesta.json()["detail"]
    assert detalle["codigo"] == "cuenta_inactiva"
    assert detalle["num_cuenta"] == CUENTA


def test_login_cuenta_inactiva_tiene_prioridad_sobre_la_contrasena(db):
    _preparar_usuario(db, activo=False)

    respuesta = _login(db, contrasena="equivocada")

    assert respuesta.status_code == 403, respuesta.text
    assert respuesta.json()["detail"]["codigo"] == "cuenta_inactiva"


def test_login_con_contrasena_incorrecta_responde_401(db):
    _preparar_usuario(db, activo=True)

    respuesta = _login(db, contrasena="equivocada")

    assert respuesta.status_code == 401, respuesta.text
    assert respuesta.json()["detail"] == "Credenciales inválidas"


def test_login_cuenta_inexistente_responde_401(db):
    respuesta = _cliente(db).post(
        "/auth/login",
        json={"num_cuenta": "20211099999", "password": CONTRASENA},
    )

    assert respuesta.status_code == 401, respuesta.text


def test_login_correcto_devuelve_token(db):
    _preparar_usuario(db, activo=True)

    respuesta = _login(db)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["rol"] == "Becario"
    assert respuesta.json()["access_token"]
