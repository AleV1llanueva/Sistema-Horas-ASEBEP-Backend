from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import List
from utils.database import get_db
from schemas.rol import RolResponse
from controllers.rol_controller import obtener_roles_controller
from core.security import admin_general

router = APIRouter()


@router.get("/roles", response_model=List[RolResponse], tags=["Roles"])
@admin_general
def obtener_roles(request: Request, db: Session = Depends(get_db)):
    return obtener_roles_controller(db)