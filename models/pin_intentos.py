from sqlalchemy import Column, Integer, String, Date
from utils.database import Base

class PinIntentos(Base):
    __tablename__ = "pin_intentos"

    id = Column(Integer, primary_key=True, index=True)
    correo = Column(String, nullable=False)
    fecha = Column(Date, nullable=False)
    intentos = Column(Integer, default=1)