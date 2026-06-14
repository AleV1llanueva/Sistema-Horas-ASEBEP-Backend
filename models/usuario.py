from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, BigInteger
from utils.database import Base
from sqlalchemy.orm import relationship

class Usuario(Base):
    __tablename__ = "usuarios"

    num_cuenta          = Column(BigInteger, primary_key=True, index=True)
    primer_nombre       = Column(String(20), nullable=False)
    segundo_nombre      = Column(String(20))
    primer_apellido     = Column(String(20), nullable=False)
    segundo_apellido    = Column(String(20))
    correo_personal     = Column(String)
    correo_institucional = Column(String, unique=True)   # corregido el typo
    carrera_id          = Column(Integer, ForeignKey("carreras.id"))
    anio_nacimiento     = Column(Integer)
    telefono            = Column(String(8))
    active              = Column(Boolean, default=True, nullable=False)  # default True
    rol_id              = Column(Integer, ForeignKey("roles.id"))
    password_hash       = Column(String, nullable=False)  # nuevo
    rol                 = relationship("Rol")