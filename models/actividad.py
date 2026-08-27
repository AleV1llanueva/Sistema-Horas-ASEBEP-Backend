# models/actividad.py
from sqlalchemy import Column, Integer, Date, Time, Text, ForeignKey
from sqlalchemy.orm import relationship
from utils.database import Base

class Actividad(Base):
    __tablename__ = "actividades"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(Text)
    descripcion = Column(Text)
    ubicacion = Column(Text)
    fecha_actividad = Column(Date)
    horas_asignar = Column(Integer)
    hora_inicio = Column(Time)
    hora_final = Column(Time)
    cupos = Column(Integer)
    estado_actividad_id = Column(Integer, ForeignKey("estados_actividad.id"))
    token_entrada = Column(Text, nullable=True)
    token_salida = Column(Text, nullable=True)
    estado = relationship("EstadoActividad")