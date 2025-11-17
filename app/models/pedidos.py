from pydantic import BaseModel
from typing import Optional

class CrearPedidoRequest(BaseModel):
    usuario_id: int

class CancelarPedidoRequest(BaseModel):
    usuario_id: int

class ActualizarSucursalRequest(BaseModel):
    sucursal_id: int