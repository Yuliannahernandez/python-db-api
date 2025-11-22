from pydantic import BaseModel

class AgregarPuntosRequest(BaseModel):
    usuarioId: int
    montoCompra: float
    pedidoId: int

class CanjearRecompensaRequest(BaseModel):
    usuarioId: int
    recompensaId: int