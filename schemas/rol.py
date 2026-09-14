from pydantic import BaseModel


class RolResponse(BaseModel):
    id: int
    nombre_rol: str

    class Config:
        from_attributes = True