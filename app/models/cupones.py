from pydantic import BaseModel

class CuponValidarRequest(BaseModel):
    codigo: str
    usuarioId: int

class CuponAplicarRequest(BaseModel):
    codigo: str
    usuarioId: int

class CuponUsoRequest(BaseModel):
    cuponCodigo: str
    clienteId: int
    pedidoId: int