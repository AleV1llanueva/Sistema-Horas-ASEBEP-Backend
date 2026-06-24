from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, BigInteger
from utils.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    num_cuenta = Column(String(13), primary_key=True, index=True)
    primer_nombre = Column(String(20))
    segundo_nombre = Column(String(20))
    primer_apellido = Column(String(20))
    segundo_apellido = Column(String(20))
    correo_personal = Column(String)
    correo_institucional = Column(String)
    carrera_id = Column(Integer, ForeignKey("carreras.id"))
    telefono = Column(String(8))
    active = Column(Boolean)
    rol_id = Column(Integer, ForeignKey("roles.id"))