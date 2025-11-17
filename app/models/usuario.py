from pydantic import BaseModel
from typing import Optional

class UsuarioCreate(BaseModel):
    correo: str
    password_Hash: str
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    telefono: Optional[str] = None
    edad: Optional[int] = None
    rol: str = "cliente"

class UsuarioUpdate(BaseModel):
    nombre: Optional[str]
    apellido: Optional[str]
    telefono: Optional[str]
    edad: Optional[int]
