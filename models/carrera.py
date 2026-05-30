from sqlalchemy import Column, Integer, String
from utils.database import Base

class Carrera(Base):
    __tablename__ = "carreras"

    id             = Column(Integer, primary_key=True, index=True)
    nombre_carrera = Column(String)