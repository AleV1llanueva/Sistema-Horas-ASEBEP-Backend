"""
Pruebas generales end-to-end contra la base de datos configurada en .env.

Cubre los dos cambios:
  1) Comentario al aceptar/rechazar aportaciones (y ajuste de monto_acumulado).
  2) Historial de actividades de un estudiante.

Crea datos con num_cuenta "TEST..." y los elimina al finalizar (try/finally).
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, time, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text

import main
from core.security import crear_token
from models.actividad import Actividad
from models.aportacion import Aportacion
from models.asistencia import Asistencia
from models.becario import Becario
from models.estado_actividad import EstadoActividad
from models.estado_asistencia import EstadoAsistencia
from models.usuario import Usuario
from utils.database import SessionLocal

CUENTA = "TEST000000001"
CUENTA2 = "TEST000000002"

OK, FAIL = "\033[92mOK\033[0m", "\033[91mFAIL\033[0m"
resultados = []


def check(nombre, cond, extra=""):
    resultados.append((nombre, cond))
    print(f"  [{OK if cond else FAIL}] {nombre}" + (f"  -> {extra}" if extra else ""))


def auth(rol, cuenta=CUENTA):
    return {"Authorization": f"Bearer {crear_token('test@unah.hn', rol, cuenta)}"}


def limpiar(db):
    for c in (CUENTA, CUENTA2):
        db.execute(text("delete from asistencias where num_cuenta = :c"), {"c": c})
        db.execute(text("delete from aportaciones where num_cuenta = :c"), {"c": c})
        db.execute(text("delete from perfiles_becarios where num_cuenta = :c"), {"c": c})
        db.execute(text("delete from usuarios where num_cuenta = :c"), {"c": c})
    db.execute(text("delete from actividades where titulo like 'TEST-%'"))
    db.commit()


def sembrar(db):
    for c in (CUENTA, CUENTA2):
        db.add(Usuario(num_cuenta=c, primer_nombre="Test", primer_apellido="QA",
                       correo_institucional=f"{c}@unah.hn"))
    db.commit()  # los usuarios deben existir antes del perfil (FK)
    for c in (CUENTA, CUENTA2):
        db.add(Becario(num_cuenta=c, monto_acumulado=0))
    db.commit()
    est_prog = db.query(EstadoActividad).filter_by(nombre_estado="Programada").first()
    est_ins = db.query(EstadoAsistencia).filter_by(nombre_estado="Inscrito").first()
    est_asis = db.query(EstadoAsistencia).filter_by(nombre_estado="Asistió").first()

    pasada = Actividad(titulo="TEST-Pasada", ubicacion="Aula 1",
                       fecha_actividad=date.today() - timedelta(days=5),
                       hora_inicio=time(9), hora_final=time(12), horas_asignar=3,
                       cupos=10, estado_actividad_id=est_prog.id)
    futura = Actividad(titulo="TEST-Futura", ubicacion="Aula 2",
                       fecha_actividad=date.today() + timedelta(days=5),
                       hora_inicio=time(14), hora_final=time(16), horas_asignar=2,
                       cupos=10, estado_actividad_id=est_prog.id)
    db.add_all([pasada, futura])
    db.commit()
    db.refresh(pasada)
    db.refresh(futura)

    db.add(Asistencia(actividad_id=pasada.id, num_cuenta=CUENTA, check_in=True,
                      check_out=True, estado_asistencia_id=est_asis.id,
                      horas_registradas=3))
    db.add(Asistencia(actividad_id=futura.id, num_cuenta=CUENTA, check_in=False,
                      check_out=False, estado_asistencia_id=est_ins.id,
                      horas_registradas=0))
    db.commit()
    return pasada, futura


def main_pruebas():
    db = SessionLocal()
    limpiar(db)
    sembrar(db)
    db.close()

    with TestClient(main.app) as cli:
        print("\n=== 1) APORTACIONES: comentario + monto ===")
        r = cli.post("/aportaciones", headers=auth("Becario"),
                     data={"num_referencia": "TEST-REF-1", "descripcion": "prueba"},
                     files={"archivo_pdf": ("a.pdf", b"%PDF-1.4 test", "application/pdf")})
        check("crear aportación (201/200)", r.status_code in (200, 201), f"{r.status_code}")
        aport_id = r.json().get("id") if r.status_code < 300 else None

        r = cli.put(f"/aportaciones/{aport_id}", headers=auth("Admin Aportaciones"),
                    json={"estado": "Rechazado"})
        check("rechazar SIN comentario -> 400", r.status_code == 400,
              f"{r.status_code} {r.json().get('detail')}")

        r = cli.put(f"/aportaciones/{aport_id}", headers=auth("Admin Aportaciones"),
                    json={"estado": "Rechazado", "comentario": "Comprobante ilegible"})
        check("rechazar CON comentario -> 200", r.status_code == 200, f"{r.status_code}")
        check("comentario devuelto", r.json().get("comentario") == "Comprobante ilegible",
              r.json().get("comentario"))

        r = cli.put(f"/aportaciones/{aport_id}", headers=auth("Admin Aportaciones"),
                    json={"estado": "Aprobado", "meses_aprobados": 3, "comentario": "Verificado"})
        check("aprobar 3 meses -> 200", r.status_code == 200, f"{r.status_code}")
        db = SessionLocal()
        monto = db.query(Becario).filter_by(num_cuenta=CUENTA).first().monto_acumulado
        check("monto_acumulado = 60 (3x20)", monto == 60, f"monto={monto}")
        db.close()

        r = cli.put(f"/aportaciones/{aport_id}", headers=auth("Admin Aportaciones"),
                    json={"estado": "Aprobado", "meses_aprobados": 5})
        db = SessionLocal()
        monto = db.query(Becario).filter_by(num_cuenta=CUENTA).first().monto_acumulado
        check("re-aprobar 5 meses -> monto 100 (delta)", monto == 100, f"monto={monto}")
        db.close()

        r = cli.put(f"/aportaciones/{aport_id}", headers=auth("Admin Aportaciones"),
                    json={"estado": "Rechazado", "comentario": "Se revierte"})
        db = SessionLocal()
        monto = db.query(Becario).filter_by(num_cuenta=CUENTA).first().monto_acumulado
        check("pasar a Rechazado revierte monto -> 0", monto == 0, f"monto={monto}")
        db.close()

        r = cli.put(f"/aportaciones/{aport_id}", headers=auth("Admin Aportaciones"),
                    json={"estado": "Aprobado", "meses_aprobados": 0})
        check("aprobar con 0 meses -> 400", r.status_code == 400, f"{r.status_code}")

        r = cli.put(f"/aportaciones/{aport_id}", headers=auth("Admin Aportaciones"),
                    json={"estado": "Aprobado", "meses_aprobados": 2, "comentario": "x" * 501})
        check("comentario > 500 chars -> 422", r.status_code == 422, f"{r.status_code}")

        r = cli.put(f"/aportaciones/{aport_id}", headers=auth("Admin Aportaciones"),
                    json={"estado": "Inexistente", "meses_aprobados": 1})
        check("estado inexistente -> 400", r.status_code == 400, f"{r.status_code}")

        r = cli.get("/becario/aportaciones", headers=auth("Becario"))
        tiene_comentario = r.status_code == 200 and "comentario" in r.json()[0]
        check("GET mis aportaciones incluye comentario", tiene_comentario)

        print("\n=== 2) HISTORIAL DE ACTIVIDADES ===")
        r = cli.get("/asistencias/historial", headers=auth("Becario"))
        check("GET /asistencias/historial -> 200", r.status_code == 200, f"{r.status_code}")
        d = r.json()
        check("solo actividades pasadas (1)", d.get("total_actividades") == 1,
              f"total={d.get('total_actividades')}")
        check("total_horas = 3", d.get("total_horas") == 3, f"total_horas={d.get('total_horas')}")
        check("titulo correcto", d["actividades"][0]["titulo"] == "TEST-Pasada",
              d["actividades"][0]["titulo"])
        check("estado 'Asistió'", d["actividades"][0]["estado"] == "Asistió",
              d["actividades"][0]["estado"])

        r = cli.get("/asistencias/historial?incluir_futuras=true", headers=auth("Becario"))
        d = r.json()
        check("incluir_futuras=true -> 2 actividades", d.get("total_actividades") == 2,
              f"total={d.get('total_actividades')}")
        fechas = [a["fecha_actividad"] for a in d["actividades"]]
        check("orden descendente por fecha", fechas == sorted(fechas, reverse=True), str(fechas))

        r = cli.get(f"/asistencias/usuarios/{CUENTA}/historial",
                    headers=auth("Admin Horas", "ADMIN00000001"))
        check("admin consulta historial de estudiante -> 200", r.status_code == 200, f"{r.status_code}")

        r = cli.get(f"/asistencias/usuarios/{CUENTA}/historial", headers=auth("Becario"))
        check("becario NO puede ver ruta admin -> 403", r.status_code == 403, f"{r.status_code}")

        r = cli.get("/asistencias/historial", headers=auth("Becario", CUENTA2))
        d = r.json()
        check("estudiante sin historial -> 0 y lista vacía",
              d.get("total_actividades") == 0 and d.get("actividades") == [], str(d))

    db = SessionLocal()
    limpiar(db)
    db.close()


if __name__ == "__main__":
    try:
        main_pruebas()
    finally:
        db = SessionLocal()
        limpiar(db)
        db.close()

    total = len(resultados)
    ok = sum(1 for _, c in resultados if c)
    print(f"\n{'='*50}\nRESULTADO: {ok}/{total} pruebas OK")
    sys.exit(0 if ok == total else 1)