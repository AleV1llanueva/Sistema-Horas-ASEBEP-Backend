"""
Configuración compartida de las pruebas.

`utils.database` crea el engine al importarse, por eso la URL de pruebas
se define aquí antes que cualquier módulo del proyecto. Cada corrida usa
una base SQLite nueva en memoria.
"""

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "clave-de-pruebas"
os.environ["DOMINIO_CORREO"] = "unah.hn"

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import models  # noqa: E402,F401  (registra todas las tablas en Base.metadata)
from core.security import crear_token  # noqa: E402
from routes.usuario import router as usuario_router  # noqa: E402
from utils.database import Base, get_db  # noqa: E402

@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    Sesion = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    sesion = Sesion()

    try:
        yield sesion
    finally:
        sesion.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def cliente(db):
    app = FastAPI()
    app.include_router(usuario_router)
    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app) as cliente_prueba:
        yield cliente_prueba


def autorizacion(rol: str, num_cuenta: str) -> dict:
    token = crear_token(
        correo=f"{num_cuenta}@unah.hn",
        rol=rol,
        num_cuenta=num_cuenta,
    )
    return {"Authorization": f"Bearer {token}"}
