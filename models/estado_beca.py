from sqlalchemy import Column, Integer, String
from utils.database import Base

class EstadoBeca(Base):
    __tablename__ = "estados_beca"

    id            = Column(Integer, primary_key=True, index=True)
    nombre_estado = Column(String(15))