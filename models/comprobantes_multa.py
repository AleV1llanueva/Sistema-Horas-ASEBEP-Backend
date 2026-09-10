from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from utils.database import Base
from datetime import datetime

class ComprobanteMulta(Base):
    __tablename__ = "comprobantes_multas"

    id = Column(Integer, primary_key=True, index=True)
    multa_id = Column(Integer, ForeignKey("multas.id"), nullable=False)
    num_cuenta = Column(String(13), ForeignKey("usuarios.num_cuenta"), nullable=False)
    num_referencia = Column(String(100), nullable=False)
    ruta_pdf = Column(String(255), nullable=False)
    estado_id = Column(Integer, ForeignKey("estados_aportacion.id"), nullable=False)
    fecha_solicitud = Column(DateTime, default=datetime.now)

    multa = relationship("Multa")
    usuario = relationship("Usuario")
    estado = relationship("EstadoAportacion")
