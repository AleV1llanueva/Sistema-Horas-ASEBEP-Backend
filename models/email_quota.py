# models/email_quota.py
from sqlalchemy import Column, Integer, Date
from utils.database import Base

class EmailQuota(Base):
    __tablename__ = "email_quota"

    fecha            = Column(Date, primary_key=True)
    correos_enviados = Column(Integer, default=0)