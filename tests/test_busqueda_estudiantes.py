"""
Pruebas del filtro `busqueda` del listado de becarios.

La misma caja de búsqueda debe encontrar al estudiante por nombre
completo (aunque esté repartido entre nombres y apellidos), por número
de cuenta, por correo institucional, por correo personal o por teléfono.
"""

import pytest

from conftest import autorizacion
from models import Becario, Carrera, EstadoBeca, Rol, Usuario

ADMIN = autorizacion("Admin General", "20209999999")

ESTUDIANTES = [
    {
        "num_cuenta": "20211000001",
        "primer_nombre": "María",
        "segundo_nombre": "José",
        "primer_apellido": "Pérez",
        "segundo_apellido": "Gómez",
        "correo_institucional": "maria.perez@unah.hn",
        "correo_personal": "majo@gmail.com",
        "telefono": "99887766",
        "carrera": "Ingeniería en Sistemas",
    },
    {
        "num_cuenta": "20211000002",
        "primer_nombre": "Luis",
        "segundo_nombre": None,
        "primer_apellido": "Martínez",
        "segundo_apellido": "Ramos",
        "correo_institucional": "luis.martinez@unah.hn",
        "correo_personal": "luismar@hotmail.com",
        "telefono": "33445566",
        "carrera": "Contaduría Pública",
    },
]


@pytest.fixture
def estudiantes(db):
    rol = Rol(nombre_rol="Becario")
    estado = EstadoBeca(nombre_estado="Activo")
    db.add_all([rol, estado])
    db.commit()

    for datos in ESTUDIANTES:
        carrera = (
            db.query(Carrera)
            .filter(Carrera.nombre_carrera == datos["carrera"])
            .first()
        )
        if not carrera:
            carrera = Carrera(nombre_carrera=datos["carrera"])
            db.add(carrera)
            db.commit()

        db.add(
            Usuario(
                num_cuenta=datos["num_cuenta"],
                primer_nombre=datos["primer_nombre"],
                segundo_nombre=datos["segundo_nombre"],
                primer_apellido=datos["primer_apellido"],
                segundo_apellido=datos["segundo_apellido"],
                correo_institucional=datos["correo_institucional"],
                correo_personal=datos["correo_personal"],
                telefono=datos["telefono"],
                carrera_id=carrera.id,
                rol_id=rol.id,
                active=True,
            )
        )
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
    return db


def _cuentas(cliente, busqueda):
    respuesta = cliente.get(
        "/usuarios",
        params={"pagina": 1, "limite": 10, "busqueda": busqueda},
        headers=ADMIN,
    )
    assert respuesta.status_code == 200, respuesta.text
    return [
        elemento["datos_personales"]["num_cuenta"]
        for elemento in respuesta.json()["elementos"]
    ]


@pytest.mark.parametrize(
    "busqueda, esperado",
    [
        ("20211000001", ["20211000001"]),
        ("maria.perez@unah.hn", ["20211000001"]),
        ("majo@gmail.com", ["20211000001"]),
        ("MARIA.PEREZ@UNAH.HN", ["20211000001"]),
        ("MARIA.PEREZ@UNAH.HN", ["20211000001"]),
        # Un número que no existe no debe traer registros.
        ("89887766", []),
        ("99887766", ["20211000001"]),
        # Nombre partido entre nombre y apellido.
        ("maria perez", ["20211000001"]),
        ("perez maria", ["20211000001"]),
        ("maria jose perez", ["20211000001"]),
        # Sin tildes se encuentra el nombre con tilde.
        ("perez", ["20211000001"]),
        ("luismar@hotmail.com", ["20211000002"]),
        ("33445566", ["20211000002"]),
        # La carrera también se busca sin tildes ni mayúsculas.
        ("contaduria", ["20211000002"]),
    ],
)
def test_busqueda_de_estudiantes(cliente, estudiantes, busqueda, esperado):
    assert _cuentas(cliente, busqueda) == esperado


def test_busqueda_sin_coincidencias_devuelve_lista_vacia(cliente, estudiantes):
    assert _cuentas(cliente, "no-existe-123") == []
