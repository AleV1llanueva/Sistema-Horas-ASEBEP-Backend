# models/estado_actividad.py
from sqlalchemy import Column, Integer, String
from utils.database import Base

class EstadoAportacion(Base):
    __tablename__ = "estados_aportacion"

    id = Column(Integer, primary_key=True, index=True)
    nombre_estado = Column(String, unique=True, index=True, nullable=False) 