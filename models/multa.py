# models/multa.py
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from utils.database import Base
from datetime import datetime

class Multa(Base):
    __tablename__ = "multas"

    id = Column(Integer, primary_key=True, index=True)
    num_cuenta = Column(String(13), ForeignKey("usuarios.num_cuenta"), nullable=False)
    actividad_id = Column(Integer, ForeignKey("actividades.id"), nullable=False)
    motivo = Column(Text, nullable=False)
    monto = Column(Integer, nullable=False, default=100)
    pagada = Column(Boolean, default=False)
    fecha_multa = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario")
    actividad = relationship("Actividad")