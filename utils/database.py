from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit = False,
    autoflush= False,
    bind= engine
)

Base = declarative_base()

def get_bg():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

try:
    with engine.connect() as connection:
        print("Conexión exitosa a la BD")
except Exception as e:
    print(f"Error en la conexión {e}")