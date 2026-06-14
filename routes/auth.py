from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from utils.database import get_db
from schemas.becario import LoginResponse
from schemas.auth import LoginInput, TokenResponse
from controllers.usuario import user_controller
from controllers.auth_controller import login_controller

from controllers.usuario import (
    user_controller
    )

router = APIRouter()

@router.get("/usuario/{num_cuenta}", response_model=LoginResponse, tags=["Becario"])
def login(num_cuenta: int, db: Session = Depends(get_db)):
    return user_controller(num_cuenta, db)


# --- Autenticación ---
@router.post("/auth/login", response_model=TokenResponse, tags=["Autenticación"])
def login(data: LoginInput, db: Session = Depends(get_db)):
    return login_controller(data, db)