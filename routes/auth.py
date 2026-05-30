from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from utils.database import get_db
from schemas.becario import LoginResponse

from controllers.usuario import (
    user_controller
    )

router = APIRouter()

@router.get("/usuario/{num_cuenta}", response_model=LoginResponse, tags=["Becario"])
def login(num_cuenta: int, db: Session = Depends(get_db)):
    return user_controller(num_cuenta, db)