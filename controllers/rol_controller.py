from sqlalchemy.orm import Session
from models.rol import Rol


def obtener_roles_controller(db: Session):
    return db.query(Rol).all()