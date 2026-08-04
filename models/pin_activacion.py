from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from utils.database import Base
from datetime import datetime

class PinActivacion(Base):
    __tablename__ = "pines_activacion"

    id = Column(Integer, primary_key= True, index=True)
    correo = Column(String, ForeignKey("usuarios.correo_institucional"), nullable=False)
    pin_hash = Column(String, nullable= False)
    expira_en = Column(DateTime, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)