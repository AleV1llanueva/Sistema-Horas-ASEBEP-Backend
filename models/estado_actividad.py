# models/estado_actividad.py
from sqlalchemy import Column, Integer, String
from utils.database import Base

class EstadoActividad(Base):
    __tablename__ = "estados_actividad"

    id = Column(Integer, primary_key=True, index=True)
    nombre_estado = Column(String)