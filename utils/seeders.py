from sqlalchemy.orm import Session
from models.estado_asistencia import EstadoAsistencia
from models.estado_actividad import EstadoActividad
from models.rol import Rol
from models.estado_beca import EstadoBeca

def ejecutar_seeders(db: Session):
    print("Ejecutando seeders de datos iniciales...")

    # 1. Estados de Asistencia
    estados_asistencia = ["Inscrito", "Asistió", "No asistió", "Cancelado"]
    for nombre in estados_asistencia:
        existe = db.query(EstadoAsistencia).filter(EstadoAsistencia.nombre_estado == nombre).first()
        if not existe:
            db.add(EstadoAsistencia(nombre_estado=nombre))

    # 2. Estados de Actividad
    estados_actividad = ["Programada", "En curso", "Completada", "Cancelada"]
    for nombre in estados_actividad:
        existe = db.query(EstadoActividad).filter(EstadoActividad.nombre_estado == nombre).first()
        if not existe:
            db.add(EstadoActividad(nombre_estado=nombre))

    # 3. Roles del Sistema (si los manejas por tabla en lugar de solo Enum)
    roles = ["Becario", "Admin General", "Admin Aportaciones", "Admin Horas"]
    for nombre in roles:
        existe = db.query(Rol).filter(Rol.nombre_rol == nombre).first()
        if not existe:
            db.add(Rol(nombre_rol=nombre))

    # 4. Estados de Beca
    estados_beca = ["Activo", "Inactivo", "Suspendido", "Finalizado"]
    for nombre in estados_beca:
        existe = db.query(EstadoBeca).filter(EstadoBeca.nombre_estado == nombre).first()
        if not existe:
            db.add(EstadoBeca(nombre_estado=nombre))

    db.commit()
    print("Seeders ejecutados exitosamente.")