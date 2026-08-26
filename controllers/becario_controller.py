from fastapi import HTTPException, Request
from datetime import date
from sqlalchemy.orm import Session

from models.usuario import Usuario
from models.becario import Becario
from models.carrera import Carrera
from models.rol import Rol
from models.estado_beca import EstadoBeca
from models.pagos import Pago

from schemas.becario import LoginResponse, Credenciales, DatosPersonales, DatosBecario, BecarioGeneralResponse

def calcular_meses_activos(mes_inicio: int, anio_inicio: int) -> list:
    fecha_actual = date.today()
    meses_activos = []
    anio_ingreso = anio_inicio
    mes_ingreso = mes_inicio

    while True:
        if anio_ingreso > fecha_actual.year or (anio_ingreso == fecha_actual.year and mes_ingreso > fecha_actual.month):
            break

        enero_especial = (mes_ingreso == 1 and anio_ingreso in [2024, 2025])

        if mes_ingreso not in [1, 12] or enero_especial:
            meses_activos.append((anio_ingreso, mes_ingreso))

        if mes_ingreso == 12:
            mes_ingreso = 1
            anio_ingreso += 1
        else:
            mes_ingreso += 1

    return meses_activos

# --- HELPER PRIVADO PARA EVITAR CÓDIGO REPETIDO ---
def _construir_detalle_becario(usuario: Usuario, becario: Becario, db: Session):
    """Construye y calcula los datos completos de un becario (horas, pagos, relaciones)."""
    
    # 1. Buscar relaciones
    carrera = db.query(Carrera).filter(Carrera.id == usuario.carrera_id).first()
    carrera_nombre = carrera.nombre_carrera if carrera else "Sin carrera"

    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    rol_nombre = rol.nombre_rol if rol else "Sin rol"

    estado_beca = db.query(EstadoBeca).filter(EstadoBeca.id == becario.estado_beca_id).first()
    estado_beca_nombre = estado_beca.nombre_estado if estado_beca else "Sin estado"

    # 2. Calcular horas
    meses_activos = calcular_meses_activos(becario.mes_inicio, becario.anio_inicio)
    horas_esperadas = len(meses_activos) * 20
    horas_faltantes = max(0, horas_esperadas - becario.horas_acumuladas)

    # 3. Calcular pagos
    pagos = db.query(Pago).filter(Pago.num_cuenta == usuario.num_cuenta).all()
    meses_pagados = set((p.fecha_pago.year, p.fecha_pago.month) for p in pagos)
    meses_sin_pagar = len([m for m in meses_activos if m not in meses_pagados])

    # 4. Retornar las estructuras listas
    credenciales = Credenciales(rol=rol_nombre, active=usuario.active)
    datos_personales = DatosPersonales(
        num_cuenta=usuario.num_cuenta,
        p_nombre=usuario.primer_nombre,
        s_nombre=usuario.segundo_nombre,
        p_apellido=usuario.primer_apellido,
        s_apellido=usuario.segundo_apellido,
        correo_personal=usuario.correo_personal,
        correo_institucional=usuario.correo_institucional,
        carrera=carrera_nombre,
        telefono=usuario.telefono
    )
    datos_becario = DatosBecario(
        periodo_inicio=becario.periodo_inicio,
        anio_inicio=becario.anio_inicio,
        horas_acumuladas=becario.horas_acumuladas,
        horas_faltantes=horas_faltantes,
        meses_sin_pagar=meses_sin_pagar,
        estado_beca=estado_beca_nombre
    )

    return credenciales, datos_personales, datos_becario

# Controlador Individual
def user_controller(num_cuenta: int, request: Request, db: Session) -> LoginResponse:
    num_cuenta_actual = getattr(request.state, "num_cuenta", None)
    rol_actual = getattr(request.state, "rol", None)

    if rol_actual == "Becario":
        if str(num_cuenta_actual) != str(num_cuenta):
            raise HTTPException(
                status_code=403,
                detail="Acceso denegado: No tienes permisos para consultar los datos de otro usuario"
            )

    usuario = db.query(Usuario).filter(Usuario.num_cuenta == num_cuenta).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    becario = db.query(Becario).filter(Becario.num_cuenta == num_cuenta).first()
    if not becario:
        raise HTTPException(status_code=403, detail="Perfil Becario no encontrado")

    credenciales, datos_personales, datos_becario = _construir_detalle_becario(usuario, becario, db)

    return LoginResponse(
        credenciales=credenciales,
        datos_personales=datos_personales,
        datos_becario=datos_becario
    )

# Controladore general
def obtener_todos_los_becarios_controller(db: Session) -> list[BecarioGeneralResponse]:
    perfiles_becarios = db.query(Becario).all()
    if not perfiles_becarios:
        return []

    resultado_general = []

    for becario in perfiles_becarios:
        usuario = db.query(Usuario).filter(Usuario.num_cuenta == becario.num_cuenta).first()
        if not usuario:
            continue

        credenciales, datos_personales, datos_becario = _construir_detalle_becario(usuario, becario, db)

        resultado_general.append(
            BecarioGeneralResponse(
                credenciales=credenciales,
                datos_personales=datos_personales,
                datos_becario=datos_becario
            )
        )

    return resultado_general