from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from sqlalchemy.orm import relationship
from utils.database import Base

class Aportacion(Base):
    __tablename__ = "aportaciones"

    id = Column(Integer, primary_key=True, index=True)
    num_cuenta = Column(String, nullable=False)
    num_referencia = Column(String, unique=True, index=True, nullable=False)
    descripcion= Column(String, nullable=True)
    ruta_pdf = Column(String, nullable=False)
    estado_aportacion_id = Column(Integer, ForeignKey("estados_aportacion.id"), nullable=False)
    fecha_subida = Column(DateTime, default=datetime.now)
    meses_aprobados = Column(Integer, nullable=False, default=0)
    estado = relationship("EstadoAportacion")
