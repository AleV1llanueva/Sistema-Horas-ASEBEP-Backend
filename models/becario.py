from sqlalchemy import Column, Integer, String, Date, ForeignKey, BigInteger
from utils.database import Base

class Becario(Base):
    __tablename__ = "perfiles_becarios"

    id = Column(Integer, primary_key=True, index=True)
    num_cuenta = Column(BigInteger, ForeignKey("usuarios.num_cuenta"))
    periodo_inicio = Column(String(10))
    anio_inicio = Column(Integer)
    mes_inicio = Column(Integer)
    horas_acumuladas = Column(Integer)
    estado_beca_id = Column(Integer, ForeignKey("estados_beca.id"))
    fecha_fin_beca = Column(Date)
    monto_acumulado = Column(Integer)
    mes_inicio = Column(Integer)