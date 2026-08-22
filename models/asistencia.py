from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from utils.database import Base

class Asistencia(Base):
    __tablename__ = "asistencias"

    id = Column(Integer, primary_key=True, index=True)
    actividad_id = Column(Integer, ForeignKey("actividades.id"))
    num_cuenta = Column(String, ForeignKey("usuarios.num_cuenta"))
    check_in = Column(Boolean, default=False)
    check_out = Column(Boolean, default=False)
    estado_asistencia_id = Column(Integer, ForeignKey("estados_asistencia.id"))
    horas_registradas = Column(Integer, default=0)

    actividad = relationship("Actividad")
    estado = relationship("EstadoAsistencia")