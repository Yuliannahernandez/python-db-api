from pydantic import BaseModel
from typing import Optional


class ProductoCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: float
    categoriaId: int
    imagenPrincipal: Optional[str] = None
    disponible: bool = True
    tiempoPreparacion: int = 15
    esNuevo: bool = False
    enTendencia: bool = False

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio: Optional[float] = None
    disponible: Optional[bool] = None
    esNuevo: Optional[bool] = None
    enTendencia: Optional[bool] = None
    
class CrearProductoDto(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: float
    categoria_id: int
    imagen_principal: Optional[str] = None
    disponible: bool = True
    tiempo_preparacion: int = 15