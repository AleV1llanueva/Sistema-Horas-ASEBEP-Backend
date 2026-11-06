import unicodedata

from sqlalchemy.sql.operators import or_

from fastapi import HTTPException, Request
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import and_

from models.usuario import Usuario
from models.becario import Becario
from models.carrera import Carrera
from models.rol import Rol
from models.estado_beca import EstadoBeca
from models.aportacion import Aportacion
from models.estado_aportación import EstadoAportacion
from models.asistencia import Asistencia

from schemas.becario import (
    BecariosPaginadosResponse,
    BecarioGeneralSinCorreoResponse,
    DatosPersonalesSinCorreo,
    LoginResponse,
    Credenciales,
    DatosPersonales,
    DatosBecario,
    BecarioGeneralResponse,
    AdminInfoResponse,
    BecarioUpdateInput,
)


def calcular_meses_activos(mes_inicio: int, anio_inicio: int) -> list:
    """
    Devuelve los meses que el becario ha estado activo.

    Los registros migrados pueden tener mes o año nulos: en ese caso
    no hay periodo válido y se devuelve una lista vacía en lugar de
    fallar al iterar.
    """
    if not mes_inicio or not anio_inicio:
        return []

    fecha_actual = date.today()
    meses_activos = []
    anio_ingreso = anio_inicio
    mes_ingreso = mes_inicio

    while True:
        if anio_ingreso > fecha_actual.year or (
            anio_ingreso == fecha_actual.year and mes_ingreso > fecha_actual.month
        ):
            break

        enero_especial = mes_ingreso == 1 and anio_ingreso in [2024, 2025]

        if mes_ingreso not in [1, 12] or enero_especial:
            meses_activos.append((anio_ingreso, mes_ingreso))

        if mes_ingreso == 12:
            mes_ingreso = 1
            anio_ingreso += 1
        else:
            mes_ingreso += 1

    return meses_activos


def calcular_horas_totales(num_cuenta: str, db: Session) -> int:
    becario = db.query(Becario).filter(Becario.num_cuenta == num_cuenta).first()
    horas_base = becario.horas_acumuladas if becario else 0

    horas_actividades = (
        db.query(func.sum(Asistencia.horas_registradas))
        .filter(Asistencia.num_cuenta == num_cuenta)
        .scalar()
        or 0
    )

    return horas_base + horas_actividades


def normalizar_busqueda(texto: Optional[str]) -> str:
    """
    Deja el texto comparable: sin tildes, sin mayúsculas y con un solo espacio.

    También se usa sobre el nombre completo del becario, para que "perez"
    encuentre a "Pérez" y "maria perez" cruce nombre y apellido.
    """
    limpio = " ".join((texto or "").split()).lower()
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", limpio)
        if unicodedata.category(caracter) != "Mn"
    )


def nombre_completo_de(usuario: Usuario) -> str:
    return normalizar_busqueda(
        " ".join(
            parte
            for parte in (
                usuario.primer_nombre,
                usuario.segundo_nombre,
                usuario.primer_apellido,
                usuario.segundo_apellido,
            )
            if parte
        )
    )


def coincide_con_el_nombre(usuario: Usuario, texto_busqueda: str) -> bool:
    """Comprueba el texto contra el nombre completo, sin importar el orden."""
    palabras = texto_busqueda.split()
    nombre = nombre_completo_de(usuario)

    if texto_busqueda in nombre:
        return True

    return len(palabras) > 1 and all(
        palabra in nombre for palabra in palabras
    )


def _coincide_sin_tildes(fila, texto_busqueda: str, por_nombre_completo=False) -> bool:
    """
    Compara una fila (becario, usuario, carrera, rol, estado) sin tildes.

    Cubre lo que el filtro de SQL no puede con `lower`: apellidos, correos,
    carrera y el nombre completo con el orden de las palabras cambiado.
    """
    becario, usuario, carrera, _, _ = fila

    if por_nombre_completo and coincide_con_el_nombre(usuario, texto_busqueda):
        return True

    return any(
        texto_busqueda in normalizar_busqueda(valor)
        for valor in (
            usuario.num_cuenta,
            usuario.primer_nombre,
            usuario.segundo_nombre,
            usuario.primer_apellido,
            usuario.segundo_apellido,
            usuario.correo_institucional,
            usuario.correo_personal,
            usuario.telefono,
            carrera.nombre_carrera if carrera else None,
        )
    )


def calcular_periodo_pac(mes_inicio: int) -> str:
    if mes_inicio <= 5:
        return "I-PAC"
    elif mes_inicio <= 8:
        return "II-PAC"
    else:
        return "III-PAC"


# --- HELPER PRIVADO PARA EVITAR CÓDIGO REPETIDO ---
def _construir_detalle_becario(usuario: Usuario, becario: Becario, db: Session):
    """Construye y calcula los datos completos de un becario (horas, pagos, relaciones)."""

    # 1. Buscar relaciones
    carrera = db.query(Carrera).filter(Carrera.id == usuario.carrera_id).first()
    carrera_nombre = carrera.nombre_carrera if carrera else "Sin carrera"

    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    rol_nombre = rol.nombre_rol if rol else "Sin rol"

    estado_beca = (
        db.query(EstadoBeca).filter(EstadoBeca.id == becario.estado_beca_id).first()
    )
    estado_beca_nombre = estado_beca.nombre_estado if estado_beca else "Sin estado"

    # 2. Calcular horas
    meses_activos = calcular_meses_activos(becario.mes_inicio, becario.anio_inicio)
    horas_esperadas = len(meses_activos) * 20
    horas_totales = calcular_horas_totales(becario.num_cuenta, db)
    horas_faltantes = max(0, horas_esperadas - horas_totales)

    # 3. Calcular pagos
    estado_aprobado = (
        db.query(EstadoAportacion)
        .filter(EstadoAportacion.nombre_estado == "Aprobado")
        .first()
    )

    total_meses_aprobados = 0
    total_meses_activos = len(meses_activos)
    meses_sin_pagar = total_meses_activos

    if estado_aprobado:
        aportaciones_aprobadas = (
            db.query(Aportacion)
            .filter(
                Aportacion.num_cuenta == usuario.num_cuenta,
                Aportacion.estado_aportacion_id == estado_aprobado.id,
            )
            .all()
        )

        total_meses_aprobados = sum(
            (a.meses_aprobados or 0) for a in aportaciones_aprobadas
        )

        # Sumar los meses cubiertos antes del sistema.
        # `monto_acumulado` guarda meses, no dinero, así que se suma
        # como entero para no producir fracciones en `meses_sin_pagar`.
        meses_aportacion_anteriores = int(becario.monto_acumulado or 0)

        total_meses_aprobados = total_meses_aprobados + meses_aportacion_anteriores

        meses_sin_pagar = max(0, int(total_meses_activos - total_meses_aprobados))

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
        telefono=usuario.telefono,
    )
    datos_becario = DatosBecario(
        periodo_inicio=becario.periodo_inicio,
        anio_inicio=becario.anio_inicio,
        mes_inicio=becario.mes_inicio,
        horas_totales=horas_totales,
        horas_faltantes=horas_faltantes,
        monto_acumulado=int(becario.monto_acumulado or 0),
        meses_sin_pagar=meses_sin_pagar,
        estado_beca=estado_beca_nombre,
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
                detail="Acceso denegado: No tienes permisos para consultar los datos de otro usuario",
            )

    usuario = db.query(Usuario).filter(Usuario.num_cuenta == num_cuenta).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    becario = db.query(Becario).filter(Becario.num_cuenta == num_cuenta).first()
    if not becario:
        raise HTTPException(status_code=403, detail="Perfil Becario no encontrado")

    credenciales, datos_personales, datos_becario = _construir_detalle_becario(
        usuario, becario, db
    )

    return LoginResponse(
        credenciales=credenciales,
        datos_personales=datos_personales,
        datos_becario=datos_becario,
    )


def _consulta_becarios(db: Session):
    """Filas base del listado: becario con correo institucional y periodo."""
    return (
        db.query(Becario, Usuario, Carrera, Rol, EstadoBeca)
        .join(Usuario, Becario.num_cuenta == Usuario.num_cuenta)
        .outerjoin(Carrera, Usuario.carrera_id == Carrera.id)
        .outerjoin(Rol, Usuario.rol_id == Rol.id)
        .outerjoin(EstadoBeca, Becario.estado_beca_id == EstadoBeca.id)
        .filter(Usuario.correo_institucional.isnot(None))
        .filter(Usuario.correo_institucional != "")
        .filter(
            and_(
                Becario.mes_inicio.isnot(None),
                Becario.mes_inicio != 0,
                Becario.anio_inicio.isnot(None),
                Becario.anio_inicio != 0,
            )
        )
    )


# Controladore general
# def obtener_todos_los_becarios_controller(db: Session) -> list[BecarioGeneralResponse]:
#     # perfiles_becarios = db.query(Becario).all()
#     #
#     perfiles_becarios = (
#         db.query(Becario)
#         .join(Usuario, Becario.num_cuenta == Usuario.num_cuenta)
#         .filter(Usuario.correo_institucional.isnot(None))
#         # Agregamos las condiciones para que mes_inicio y anio_inicio no sean nulos ni 0
#         .filter(
#             and_(
#                 Becario.mes_inicio.isnot(None),
#                 Becario.mes_inicio != 0,
#                 Becario.anio_inicio.isnot(None),
#                 Becario.anio_inicio != 0,
#             )
#         )
#         .all()
#     )
#
#     if not perfiles_becarios:
#         return []
#
#     resultado_general = []
#
#     for becario in perfiles_becarios:
#         usuario = (
#             db.query(Usuario).filter(Usuario.num_cuenta == becario.num_cuenta).first()
#         )
#         if not usuario:
#             continue
#
#         credenciales, datos_personales, datos_becario = _construir_detalle_becario(
#             usuario, becario, db
#         )
#
#         resultado_general.append(
#             BecarioGeneralResponse(
#                 credenciales=credenciales,
#                 datos_personales=datos_personales,
#                 datos_becario=datos_becario,
#             )
#         )
#
#     return resultado_general


def obtener_todos_los_becarios_controller(
    db: Session,
    pagina: Optional[int] = None,
    limite: Optional[int] = None,
    busqueda: Optional[str] = None,
    activo: Optional[bool] = None,
) -> BecariosPaginadosResponse:
    """
    Devuelve los becarios registrados.

    Si se envían pagina y limite, el cálculo de totales y agrupaciones
    se realiza solo sobre el conjunto filtrado, y los totales de horas y
    aportaciones se calculan únicamente para los becarios de la página.
    """
    texto_busqueda = normalizar_busqueda(busqueda)

    # Filtro por campos sueltos: cuenta, nombres, apellidos, correos,
    # teléfono y carrera. Se usa `lower` en lugar de `ilike` para que
    # funcione igual en PostgreSQL y SQLite.
    filtro_busqueda = None
    if texto_busqueda:
        patron = f"%{texto_busqueda}%"
        filtro_busqueda = or_(
            func.lower(Usuario.num_cuenta).like(patron),
            func.lower(Usuario.primer_nombre).like(patron),
            func.lower(Usuario.segundo_nombre).like(patron),
            func.lower(Usuario.primer_apellido).like(patron),
            func.lower(Usuario.segundo_apellido).like(patron),
            func.lower(Usuario.correo_institucional).like(patron),
            func.lower(Usuario.correo_personal).like(patron),
            Usuario.telefono.like(patron),
            func.lower(Carrera.nombre_carrera).like(patron),
        )

    # 1. Obtener el ID del estado "Aprobado" UNA SOLA VEZ
    estado_aprobado = (
        db.query(EstadoAportacion)
        .filter(EstadoAportacion.nombre_estado == "Aprobado")
        .first()
    )
    estado_aprobado_id = estado_aprobado.id if estado_aprobado else None

    def consultar(aplicar_busqueda: bool):
        consulta = _consulta_becarios(db)

        if activo is not None:
            consulta = consulta.filter(Usuario.active.is_(activo))

        if aplicar_busqueda and filtro_busqueda is not None:
            consulta = consulta.filter(filtro_busqueda)

        return consulta.order_by(
            Usuario.primer_apellido, Usuario.primer_nombre
        ).all()

    filas_filtradas = consultar(aplicar_busqueda=True)

    # El filtro de SQL no quita tildes: "contauduria" no encuentra
    # "Contaduría" y "perez" no encuentra "Pérez". Se agregan en
    # memoria los registros que coinciden sin tildes y por nombre completo.
    if texto_busqueda:
        cuentas_incluidas = {fila[0].num_cuenta for fila in filas_filtradas}
        filas_filtradas = sorted(
            filas_filtradas
            + [
                fila
                for fila in consultar(aplicar_busqueda=False)
                if fila[0].num_cuenta not in cuentas_incluidas
                and _coincide_sin_tildes(
                    fila, texto_busqueda, por_nombre_completo=True
                )
            ],
            key=lambda fila: (
                (fila[1].primer_apellido or ""),
                (fila[1].primer_nombre or ""),
                fila[0].num_cuenta,
            ),
        )

    usar_paginacion = pagina is not None and limite is not None
    total = len(filas_filtradas)

    if usar_paginacion:
        inicio = (pagina - 1) * limite
        resultados_base = filas_filtradas[inicio: inicio + limite]
    else:
        resultados_base = filas_filtradas

    if not resultados_base:
        return BecariosPaginadosResponse(
            elementos=[],
            total=total,
            pagina=pagina or 1,
            limite=limite or 0,
            total_paginas=0,
        )

    # 3. Agrupar asistencias solo para los becarios consultados
    cuentas = [becario.num_cuenta for becario, _, _, _, _ in resultados_base]

    asistencias = (
        db.query(
            Asistencia.num_cuenta,
            func.sum(Asistencia.horas_registradas).label("total_horas"),
        )
        .filter(Asistencia.num_cuenta.in_(cuentas))
        .group_by(Asistencia.num_cuenta)
        .all()
    )
    # Convertir a un diccionario para búsqueda rápida en memoria { "numero_cuenta": horas_totales }
    mapa_asistencias = {num: total_horas or 0 for num, total_horas in asistencias}

    # 4. Agrupar aportaciones aprobadas solo para los becarios consultados
    mapa_aportaciones = {}
    if estado_aprobado_id:
        aportaciones = (
            db.query(
                Aportacion.num_cuenta,
                func.sum(Aportacion.meses_aprobados).label("total_meses"),
            )
            .filter(Aportacion.estado_aportacion_id == estado_aprobado_id)
            .filter(Aportacion.num_cuenta.in_(cuentas))
            .group_by(Aportacion.num_cuenta)
            .all()
        )
        mapa_aportaciones = {num: total_meses or 0 for num, total_meses in aportaciones}

    # 5. Ensamblar la respuesta en memoria (CERO consultas a la BD dentro del bucle)
    resultado_general = []

    for becario, usuario, carrera, rol, estado_beca in resultados_base:
        num_cuenta = becario.num_cuenta

        # Nombres de relaciones
        carrera_nombre = carrera.nombre_carrera if carrera else "Sin carrera"
        rol_nombre = rol.nombre_rol if rol else "Sin rol"
        estado_beca_nombre = estado_beca.nombre_estado if estado_beca else "Sin estado"

        # Calcular horas (100% en memoria)
        meses_activos = calcular_meses_activos(becario.mes_inicio, becario.anio_inicio)
        horas_esperadas = len(meses_activos) * 20

        horas_base = becario.horas_acumuladas if becario.horas_acumuladas else 0
        horas_actividades = mapa_asistencias.get(num_cuenta, 0)
        horas_totales = horas_base + horas_actividades
        horas_faltantes = max(0, horas_esperadas - horas_totales)

        # Calcular pagos (100% en memoria)
        total_meses_aprobados = mapa_aportaciones.get(num_cuenta, 0)

        # Coincide con _construir_detalle_becario: los meses cubiertos
        # antes del sistema también cuentan como aportados y son enteros.
        total_meses_aprobados += int(becario.monto_acumulado or 0)

        total_meses_activos = len(meses_activos)
        meses_sin_pagar = max(0, int(total_meses_activos - total_meses_aprobados))

        # Crear schemas Pydantic
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
            telefono=usuario.telefono,
        )
        datos_becario = DatosBecario(
            periodo_inicio=becario.periodo_inicio,
            anio_inicio=becario.anio_inicio,
            mes_inicio=becario.mes_inicio,
            horas_totales=horas_totales,
            horas_faltantes=horas_faltantes,
            monto_acumulado=int(becario.monto_acumulado or 0),
            meses_sin_pagar=meses_sin_pagar,
            estado_beca=estado_beca_nombre,
        )

        resultado_general.append(
            BecarioGeneralResponse(
                credenciales=credenciales,
                datos_personales=datos_personales,
                datos_becario=datos_becario,
            )
        )

    return BecariosPaginadosResponse(
        elementos=resultado_general,
        total=total,
        pagina=pagina or 1,
        limite=limite or 0,
        total_paginas=(
            (total + limite - 1) // limite if usar_paginacion and limite else 0
        ),
    )


def obtener_becarios_sin_correo_controller(db: Session) -> list[BecarioGeneralSinCorreoResponse]:
    # 1. Obtener el ID del estado "Aprobado" UNA SOLA VEZ
    estado_aprobado = (
        db.query(EstadoAportacion)
        .filter(EstadoAportacion.nombre_estado == "Aprobado")
        .first()
    )
    estado_aprobado_id = estado_aprobado.id if estado_aprobado else None

    # 2. Obtener TODOS los datos base usando JOINs en UNA SOLA CONSULTA
    resultados_base = (
        db.query(Becario, Usuario, Carrera, Rol, EstadoBeca)
        .join(Usuario, Becario.num_cuenta == Usuario.num_cuenta)
        .outerjoin(Carrera, Usuario.carrera_id == Carrera.id)
        .outerjoin(Rol, Usuario.rol_id == Rol.id)
        .outerjoin(EstadoBeca, Becario.estado_beca_id == EstadoBeca.id)
        .filter(or_(Usuario.correo_institucional.is_(None), Usuario.correo_institucional == ''))
        .filter(
            and_(
                Becario.mes_inicio.isnot(None),
                Becario.mes_inicio != 0,
                Becario.anio_inicio.isnot(None),
                Becario.anio_inicio != 0,
            )
        )
        .all()
    )

    if not resultados_base:
        return []

    # 3. Obtener TODAS las asistencias agrupadas por número de cuenta en UNA CONSULTA
    asistencias = (
        db.query(
            Asistencia.num_cuenta,
            func.sum(Asistencia.horas_registradas).label("total_horas"),
        )
        .group_by(Asistencia.num_cuenta)
        .all()
    )
    # Convertir a un diccionario para búsqueda rápida en memoria { "numero_cuenta": horas_totales }
    mapa_asistencias = {num: total or 0 for num, total in asistencias}

    # 4. Obtener TODAS las aportaciones agrupadas por número de cuenta en UNA CONSULTA
    mapa_aportaciones = {}
    if estado_aprobado_id:
        aportaciones = (
            db.query(
                Aportacion.num_cuenta,
                func.sum(Aportacion.meses_aprobados).label("total_meses"),
            )
            .filter(Aportacion.estado_aportacion_id == estado_aprobado_id)
            .group_by(Aportacion.num_cuenta)
            .all()
        )
        mapa_aportaciones = {num: total or 0 for num, total in aportaciones}

    # 5. Ensamblar la respuesta en memoria (CERO consultas a la BD dentro del bucle)
    resultado_general = []

    for becario, usuario, carrera, rol, estado_beca in resultados_base:
        num_cuenta = becario.num_cuenta

        # Nombres de relaciones
        carrera_nombre = carrera.nombre_carrera if carrera else "Sin carrera"
        rol_nombre = rol.nombre_rol if rol else "Sin rol"
        estado_beca_nombre = estado_beca.nombre_estado if estado_beca else "Sin estado"

        # Calcular horas (100% en memoria)
        meses_activos = calcular_meses_activos(becario.mes_inicio, becario.anio_inicio)
        horas_esperadas = len(meses_activos) * 20

        horas_base = becario.horas_acumuladas if becario.horas_acumuladas else 0
        horas_actividades = mapa_asistencias.get(num_cuenta, 0)
        horas_totales = horas_base + horas_actividades
        horas_faltantes = max(0, horas_esperadas - horas_totales)

        # Calcular pagos (100% en memoria)
        total_meses_aprobados = mapa_aportaciones.get(num_cuenta, 0)

        # Coincide con _construir_detalle_becario: los meses cubiertos
        # antes del sistema también cuentan como aportados y son enteros.
        total_meses_aprobados += int(becario.monto_acumulado or 0)

        total_meses_activos = len(meses_activos)
        meses_sin_pagar = max(0, int(total_meses_activos - total_meses_aprobados))

        # Crear schemas Pydantic
        credenciales = Credenciales(rol=rol_nombre, active=usuario.active)
        datos_personales = DatosPersonalesSinCorreo(
            num_cuenta=usuario.num_cuenta,
            p_nombre=usuario.primer_nombre,
            s_nombre=usuario.segundo_nombre,
            p_apellido=usuario.primer_apellido,
            s_apellido=usuario.segundo_apellido,
            correo_personal=usuario.correo_personal,
            correo_institucional=usuario.correo_institucional,
            carrera=carrera_nombre,
            telefono=usuario.telefono,
        )
        datos_becario = DatosBecario(
            periodo_inicio=becario.periodo_inicio,
            anio_inicio=becario.anio_inicio,
            mes_inicio=becario.mes_inicio,
            horas_totales=horas_totales,
            horas_faltantes=horas_faltantes,
            monto_acumulado=int(becario.monto_acumulado or 0),
            meses_sin_pagar=meses_sin_pagar,
            estado_beca=estado_beca_nombre,
        )

        resultado_general.append(
            BecarioGeneralSinCorreoResponse(
                credenciales=credenciales,
                datos_personales=datos_personales,
                datos_becario=datos_becario,
            )
        )

    return resultado_general

def usuario_me_controller(request: Request, db: Session):
    num_cuenta_actual = getattr(request.state, "num_cuenta", None)
    rol_actual = getattr(request.state, "rol", None)

    usuario = db.query(Usuario).filter(Usuario.num_cuenta == num_cuenta_actual).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # if rol_actual == "Becario":
    #     becario = db.query(Becario).filter(Becario.num_cuenta == num_cuenta_actual).first()
    #     if not becario:
    #         raise HTTPException(status_code=403, detail="Perfil Becario no encontrado")
    #
    #     credenciales, datos_personales, datos_becario = _construir_detalle_becario(usuario, becario, db)
    #     return LoginResponse(
    #         credenciales=credenciales,
    #         datos_personales=datos_personales,
    #         datos_becario=datos_becario
    #     )
    #
    # Es admin (Admin General, Admin Aportaciones, o Admin Horas)
    #
    # ------Este cambio será temporal, en caso de que vea que la demas info no se usa, se hara una restructuracion
    #
    # return AdminInfoResponse(
    #     num_cuenta=usuario.num_cuenta,
    #     primer_nombre=usuario.primer_nombre,
    #     segundo_nombre=usuario.segundo_nombre,
    #     primer_apellido=usuario.primer_apellido,
    #     segundo_apellido=usuario.segundo_apellido,
    #     correo_institucional=usuario.correo_institucional,
    #     rol=rol_actual
    # )
    #
    #

    becario = db.query(Becario).filter(Becario.num_cuenta == num_cuenta_actual).first()
    if not becario:
        raise HTTPException(status_code=403, detail="Perfil Becario no encontrado")

    credenciales, datos_personales, datos_becario = _construir_detalle_becario(
        usuario, becario, db
    )
    return LoginResponse(
        credenciales=credenciales,
        datos_personales=datos_personales,
        datos_becario=datos_becario,
    )


def obtener_estado_beca_id(nombre_estado: str, db: Session) -> int:
    estado = (
        db.query(EstadoBeca).filter(EstadoBeca.nombre_estado == nombre_estado).first()
    )
    if not estado:
        raise HTTPException(
            status_code=500, detail=f"Estado de beca '{nombre_estado}' no configurado"
        )
    return estado.id


def verificar_y_finalizar_por_fecha(becario: Becario, db: Session):
    if becario.fecha_fin_beca and becario.fecha_fin_beca <= date.today():
        estado_actual = becario.estado.nombre_estado if becario.estado else None
        if estado_actual != "Finalizado":
            becario.estado_beca_id = obtener_estado_beca_id("Finalizado", db)
            db.commit()
            db.refresh(becario)


def desactivar_becario_controller(num_cuenta: str, db: Session):
    becario = db.query(Becario).filter(Becario.num_cuenta == num_cuenta).first()
    if not becario:
        raise HTTPException(status_code=404, detail="Perfil de becario no encontrado")

    estado_actual = becario.estado.nombre_estado if becario.estado else None
    if estado_actual == "Inactivo":
        raise HTTPException(status_code=400, detail="El becario ya está inactivo")

    becario.estado_beca_id = obtener_estado_beca_id("Inactivo", db)
    db.commit()
    return {"mensaje": "Becario desactivado exitosamente"}


def reactivar_becario_controller(num_cuenta: str, db: Session):
    becario = db.query(Becario).filter(Becario.num_cuenta == num_cuenta).first()
    if not becario:
        raise HTTPException(status_code=404, detail="Perfil de becario no encontrado")

    estado_actual = becario.estado.nombre_estado if becario.estado else None
    if estado_actual == "Activo":
        raise HTTPException(status_code=400, detail="El becario ya está activo")

    becario.estado_beca_id = obtener_estado_beca_id("Activo", db)
    db.commit()
    return {"mensaje": "Becario reactivado exitosamente"}


def actualizar_becario_controller(
    num_cuenta: str, datos: BecarioUpdateInput, db: Session
):
    actualizar_perfil_becario(num_cuenta, datos, db)
    return obtener_datos_becario(num_cuenta, db)


def obtener_datos_becario(
    num_cuenta: str,
    db: Session,
) -> DatosBecario:
    becario = db.query(Becario).filter(Becario.num_cuenta == num_cuenta).first()
    if not becario:
        raise HTTPException(status_code=404, detail="Perfil de becario no encontrado")

    usuario = db.query(Usuario).filter(Usuario.num_cuenta == num_cuenta).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    _, _, datos_becario = _construir_detalle_becario(usuario, becario, db)
    return datos_becario


def actualizar_becario_por_admin_controller(
    num_cuenta: str,
    datos: BecarioUpdateInput,
    db: Session,
) -> DatosBecario:
    """
    Punto de entrada para los administradores generales.

    Mantiene el mismo cálculo de respuesta que usan las pantallas
    administrativas y registra en el log cada cambio de horas,
    aportaciones o periodo de ingreso, porque corresponden a datos
    previos a la migración al sistema.
    """
    actualizar_perfil_becario(num_cuenta, datos, db)

    cambios = {
        campo: valor
        for campo, valor in {
            "horas_acumuladas": datos.horas_acumuladas,
            "meses_aportados": datos.monto_acumulado,
            "anio_inicio": datos.anio_inicio,
            "mes_inicio": datos.mes_inicio,
        }.items()
        if valor is not None
    }

    if cambios:
        print(f"[admin] Ajuste manual del becario {num_cuenta}: {cambios}")

    return obtener_datos_becario(num_cuenta, db)


def actualizar_perfil_becario(
    num_cuenta: str,
    datos: BecarioUpdateInput,
    db: Session,
) -> None:
    becario = db.query(Becario).filter(Becario.num_cuenta == num_cuenta).first()
    if not becario:
        raise HTTPException(status_code=404, detail="Perfil de becario no encontrado")

    usuario = db.query(Usuario).filter(Usuario.num_cuenta == num_cuenta).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if datos.estado_beca_id is not None:
        estado = (
            db.query(EstadoBeca).filter(EstadoBeca.id == datos.estado_beca_id).first()
        )
        if not estado:
            raise HTTPException(status_code=404, detail="Estado de beca no encontrado")
        becario.estado_beca_id = datos.estado_beca_id

    if datos.anio_inicio is not None:
        becario.anio_inicio = datos.anio_inicio

    if datos.mes_inicio is not None:
        becario.mes_inicio = datos.mes_inicio
        becario.periodo_inicio = calcular_periodo_pac(datos.mes_inicio)

    if datos.horas_acumuladas is not None:
        becario.horas_acumuladas = datos.horas_acumuladas
    if datos.monto_acumulado is not None:
        becario.monto_acumulado = datos.monto_acumulado

    if datos.fecha_fin_beca is not None:
        becario.fecha_fin_beca = datos.fecha_fin_beca

        estado_actual = becario.estado.nombre_estado if becario.estado else None
        if datos.fecha_fin_beca >= date.today() and estado_actual == "Finalizado":
            becario.estado_beca_id = obtener_estado_beca_id("Activo", db)

    db.commit()
    db.refresh(becario)

    verificar_y_finalizar_por_fecha(becario, db)
