from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # Sube de 5 a 20 conexiones base
    max_overflow=30,       # Permite hasta 30 extras en picos (50 total)
    pool_timeout=30,       # Tiempo máximo de espera antes de lanzar error
    pool_pre_ping=True,    # Comprueba que la conexión esté viva antes de usarla
    pool_recycle=1800,     # Renueva conexiones cada 30 min para evitar cortes
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
