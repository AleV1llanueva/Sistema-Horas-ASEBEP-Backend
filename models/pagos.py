from sqlalchemy import Column, Integer, ForeignKey, DateTime, BigInteger
from utils.database import Base

class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    num_cuenta = Column(BigInteger, ForeignKey("usuarios.num_cuenta"))
    monto = Column(Integer)
    fecha_pago = Column(DateTime)
    estado_pago_id = Column(Integer, ForeignKey("estados_pago.id"))
    tipo_pago_id  = Column(Integer, ForeignKey("tipos_pago.id"))