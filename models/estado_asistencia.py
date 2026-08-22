from sqlalchemy import Column, Integer, String
from utils.database import Base

class EstadoAsistencia(Base):
    __tablename__ = "estados_asistencia"

    id = Column(Integer, primary_key=True, index=True)
    nombre_estado = Column(String)