import utils.database
from fastapi import FastAPI

from models import pin_activacion

from routes.auth import router as auth_routers

app = FastAPI()

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