from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.auth import router as auth_routers
from routes.usuario import router as usuario_router
from routes.actividad import router as actividad_router
from routes.asistencia import router as asistencia_router 
from utils.database import SessionLocal
from utils.seeders import ejecutar_seeders

app = FastAPI()

# Define los orígenes permitidos (URLs de tu frontend)
origins = [
    "http://localhost:3000",        # Desarrollo local (React/Next.js/Vue)
    "http://localhost:5173",        # Desarrollo local (Vite)
    "https://asebepunah.com",        # Tu frontend en producción
    "https://www.asebepunah.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # O usa ["*"] solo para pruebas/APIs públicas
    allow_credentials=True,         # Permitir cookies y encabezados de autenticación
    allow_methods=["*"],            # Permitir todos los métodos (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],            # Permitir todos los encabezados
)

@app.get("/")
def read_root():
    return {"message": "API con CORS configurado"}

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