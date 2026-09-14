from sqlalchemy import Column, Integer, String, Boolean
from utils.database import Base

class Carrera(Base):
    __tablename__ = "carreras"

    id = Column(Integer, primary_key=True, index=True)
    nombre_carrera = Column(String)
    activo = Column(Boolean, default=True, nullable=False)