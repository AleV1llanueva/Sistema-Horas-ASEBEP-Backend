"""
Pruebas de la eliminación definitiva de estudiantes.

Un estudiante solo puede borrarse si ninguna otra tabla lo referencia;
si las hay, la respuesta dice cuáles y no borra nada.
"""

from conftest import autorizacion
from models import Asistencia, Aportacion, EstadoAportacion, Multa, Usuario
from tests.test_crear_estudiante import (
    CUENTA_EXISTENTE,
    _crear_estudiante,
    _preparar_catalogo,
)

ADMIN = autorizacion("Admin General", "20209999999")
OTRO_ADMIN = autorizacion("Admin Horas", "20209999998")


def _asistencia(db, num_cuenta):
    db.add(Asistencia(actividad_id=1, num_cuenta=num_cuenta))
    db.commit()


def _aportacion(db, num_cuenta):
    estado = EstadoAportacion(nombre_estado="Aprobado")
    db.add(estado)
    db.commit()
    db.add(
        Aportacion(
            num_cuenta=num_cuenta,
            num_referencia="REF-001",
            ruta_pdf="uploads/ref.pdf",
            estado_aportacion_id=estado.id,
        )
    )
    db.commit()


def _multa(db, num_cuenta):
    db.add(Multa(num_cuenta=num_cuenta, actividad_id=1, motivo="Ausencia"))
    db.commit()


def test_eliminar_estudiante_sin_referencias_lo_borra(cliente, db):
    rol, carrera, estado = _preparar_catalogo(db)
    _crear_estudiante(db, rol, carrera, estado)

    respuesta = cliente.delete(
        f"/usuarios/{CUENTA_EXISTENTE}",
        headers=ADMIN,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert db.query(Usuario).filter_by(num_cuenta=CUENTA_EXISTENTE).first() is None
    assert respuesta.json()["eliminados"]["perfiles_becarios"] == 1


def test_eliminar_estudiante_con_referencias_indica_cuales(cliente, db):
    rol, carrera, estado = _preparar_catalogo(db)
    _crear_estudiante(db, rol, carrera, estado)
    _asistencia(db, CUENTA_EXISTENTE)
    _multa(db, CUENTA_EXISTENTE)

    respuesta = cliente.delete(
        f"/usuarios/{CUENTA_EXISTENTE}",
        headers=ADMIN,
    )

    assert respuesta.status_code == 409, respuesta.text
    detalle = respuesta.json()["detail"]
    assert detalle["campo"] == "referencias"
    assert detalle["num_cuenta"] == CUENTA_EXISTENTE
    assert detalle["referencias"] == {"asistencias": 1, "multas": 1}
    assert db.query(Usuario).filter_by(num_cuenta=CUENTA_EXISTENTE).first() is not None


def test_eliminar_estudiante_con_aportacion_no_borra_nada(cliente, db):
    rol, carrera, estado = _preparar_catalogo(db)
    _crear_estudiante(db, rol, carrera, estado)
    _aportacion(db, CUENTA_EXISTENTE)

    respuesta = cliente.delete(
        f"/usuarios/{CUENTA_EXISTENTE}",
        headers=ADMIN,
    )

    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json()["detail"]["referencias"] == {"aportaciones": 1}
    assert db.query(Aportacion).count() == 1


def test_eliminar_estudiante_inexistente_responde_404(cliente, db):
    _preparar_catalogo(db)

    respuesta = cliente.delete(
        "/usuarios/20211099999",
        headers=ADMIN,
    )

    assert respuesta.status_code == 404, respuesta.text


def test_eliminar_exige_admin_general(cliente, db):
    rol, carrera, estado = _preparar_catalogo(db)
    _crear_estudiante(db, rol, carrera, estado)

    respuesta = cliente.delete(
        f"/usuarios/{CUENTA_EXISTENTE}",
        headers=OTRO_ADMIN,
    )

    assert respuesta.status_code == 403, respuesta.text
    assert db.query(Usuario).filter_by(num_cuenta=CUENTA_EXISTENTE).first() is not None
