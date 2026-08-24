from fastapi import FastAPI

from routes.auth import router as auth_routers
from routes.usuario import router as usuario_router
from routes.actividad import router as actividad_router
from routes.asistencia import router as asistencia_router 
from utils.database import SessionLocal
from utils.seeders import ejecutar_seeders

app = FastAPI()

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        ejecutar_seeders(db)
    finally:
        db.close()

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def read_root():
    return {"status": "healthy", "version": "0.0.0", "service": "ASEBEP-API"}

app.include_router(auth_routers)
app.include_router(usuario_router)
app.include_router(actividad_router)
app.include_router(asistencia_router)