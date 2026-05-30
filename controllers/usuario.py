from fastapi import HTTPException
from datetime import date

from sqlalchemy.orm import Session
from models.usuario import Usuario
from models.becario import Becario
from models.carrera import Carrera
from models.rol import Rol
from models.estado_beca import EstadoBeca
from models.pagos import Pago

from schemas.becario import LoginResponse, Credenciales, DatosPersonales, DatosBecario

def calcular_meses_activos(mes_inicio: int, anio_inicio: int) -> list:
    """
    Calcula los meses activos desde el inicio de la beca hasta hoy, excluyendo enero (1) y diciembre (12)
    """
    fecha_actual = date.today()
    meses_activos = []

    anio_ingreso = anio_inicio
    mes_ingreso = mes_inicio

    while True:
        if anio_ingreso > fecha_actual.year or (anio_ingreso == fecha_actual.year and mes_ingreso > fecha_actual.month):
            break

        if mes_ingreso not in [1, 12]:
            meses_activos.append((anio_ingreso, mes_ingreso))

        if mes_ingreso == 12:
            mes_ingreso = 1
            anio_ingreso += 1
        else:
            mes_ingreso += 1

    return meses_activos

def user_controller(num_cuenta: int, db: Session):
    """
    Obtiene la información completa de un usuario becario. 
    Realiza consultas a las tablas: usuarios, perfiles_becarios, carreras, roles, estados_becas y pagos para construir el response 
    """
    #Buscar usuario por número de cuenta 
    usuario = db.query(Usuario).filter(Usuario.num_cuenta == num_cuenta).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    #Buscar perfil de becario asociado al usuario
    becario = db.query(Becario).filter(Becario.num_cuenta == num_cuenta).first()

    #Buscar carrera, rol y estado de beca por sus IDs
    carrera = db.query(Carrera).filter(Carrera.id == usuario.carrera_id).first()
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    estado_beca = db.query(EstadoBeca).filter(EstadoBeca.id == becario.estado_beca_id).first()

    #Calcular horas
    meses_activos = calcular_meses_activos(becario.mes_inicio, becario.anio_inicio)
    horas_esperadas = len(meses_activos) * 20
    horas_faltantes = max(0, horas_esperadas - becario.horas_acumuladas)

    #Calcular pagos
    pagos = db.query(Pago).filter(Pago.num_cuenta == num_cuenta).all()
    meses_pagados = set()
    for pago in pagos:
        meses_pagados.add((pago.fecha_pago.year, pago.fecha_pago.month))
    meses_sin_pagar = len([m for m in meses_activos if m not in meses_pagados])

    #Construir y retornar el response 
    return LoginResponse(
        credenciales=Credenciales(
            rol=rol.nombre_rol,
            active=usuario.active
        ),
        datos_personales=DatosPersonales(
            num_cuenta=usuario.num_cuenta,
            p_nombre=usuario.primer_nombre,
            s_nombre=usuario.segundo_nombre,
            p_apellido=usuario.primer_apellido,
            s_apellido=usuario.segundo_apellido,
            correo_personal=usuario.correo_personal,
            correo_inst=usuario.correo_intitucional,
            carrera=carrera.nombre_carrera,
            anio_nacimiento=usuario.anio_nacimiento,
            telefono=usuario.telefono
        ),
        datos_becario=DatosBecario(
            periodo_inicio=becario.periodo_inicio,
            anio_inicio=becario.anio_inicio,
            horas_acumuladas=becario.horas_acumuladas,
            horas_faltantes=horas_faltantes,
            meses_sin_pagar=meses_sin_pagar,
            estado_beca=estado_beca.nombre_estado
        )
    )