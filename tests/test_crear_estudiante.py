"""
Pruebas del alta de estudiantes desde el panel administrativo.

Cubren que el backend indique qué dato está repetido cuando el número de
cuenta o el correo institucional ya existen.
"""

from conftest import autorizacion
from models import Becario, Carrera, EstadoBeca, Rol, Usuario

CUENTA_EXISTENTE = "20211000001"
CUENTA_NUEVA = "20211000002"
ADMIN = autorizacion("Admin General", "20209999999")


def _preparar_catalogo(db):
    rol = Rol(nombre_rol="Becario")
    carrera = Carrera(nombre_carrera="Ingeniería en Sistemas")
    estado = EstadoBeca(nombre_estado="Activo")
    db.add_all([rol, carrera, estado])
    db.commit()
    return rol, carrera, estado


def _crear_estudiante(db, rol, carrera, estado, **cambios):
    datos = {
        "num_cuenta": CUENTA_EXISTENTE,
        "primer_nombre": "Ana",
        "primer_apellido": "López",
        "correo_institucional": "ana.lopez@unah.hn",
        "correo_personal": "ana@gmail.com",
        "telefono": "99998888",
        "carrera_id": carrera.id,
        "rol_id": rol.id,
        "active": True,
    }
    datos.update(cambios)

    db.add(Usuario(**datos))
    db.add(
        Becario(
            num_cuenta=datos["num_cuenta"],
            periodo_inicio="I-PAC",
            anio_inicio=2024,
            mes_inicio=3,
            horas_acumuladas=0,
            monto_acumulado=0,
            estado_beca_id=estado.id,
        )
    )
    db.commit()


def _formulario(carrera, **cambios):
    datos = {
        "num_cuenta": CUENTA_NUEVA,
        "primer_nombre": "Luis",
        "primer_apellido": "Martínez",
        "correo_institucional": "luis.martinez@unah.hn",
        "correo_personal": "luis@gmail.com",
        "telefono": "88887777",
        "carrera_id": carrera.id,
        "mes_inicio": 3,
        "anio_inicio": 2025,
    }
    datos.update(cambios)
    return datos


def test_crear_estudiante_duplicado_indica_numero_de_cuenta(cliente, db):
    rol, carrera, estado = _preparar_catalogo(db)
    _crear_estudiante(db, rol, carrera, estado)

    respuesta = cliente.post(
        "/usuarios",
        json=_formulario(carrera, num_cuenta=CUENTA_EXISTENTE),
        headers=ADMIN,
    )

    assert respuesta.status_code == 409, respuesta.text
    detalle = respuesta.json()["detail"]
    assert detalle["campo"] == "num_cuenta"
    assert detalle["num_cuenta"] == CUENTA_EXISTENTE


def test_crear_estudiante_duplicado_indica_correo_institucional(cliente, db):
    rol, carrera, estado = _preparar_catalogo(db)
    _crear_estudiante(db, rol, carrera, estado)

    respuesta = cliente.post(
        "/usuarios",
        json=_formulario(
            carrera,
            correo_institucional="ana.lopez@unah.hn",
        ),
        headers=ADMIN,
    )

    assert respuesta.status_code == 409, respuesta.text
    detalle = respuesta.json()["detail"]
    assert detalle["campo"] == "correo_institucional"
    assert detalle["num_cuenta"] == CUENTA_EXISTENTE
    assert detalle["correo_institucional"] == "ana.lopez@unah.hn"


def test_crear_estudiante_sin_duplicados_responde_201(cliente, db):
    rol, carrera, estado = _preparar_catalogo(db)
    _crear_estudiante(db, rol, carrera, estado)

    respuesta = cliente.post(
        "/usuarios",
        json=_formulario(carrera),
        headers=ADMIN,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["num_cuenta"] == CUENTA_NUEVA
