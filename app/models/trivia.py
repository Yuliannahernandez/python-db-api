from pydantic import BaseModel
from typing import Optional

class IniciarPartidaRequest(BaseModel):
    usuarioId: int
    pedidoId: Optional[int] = None

class ResponderPreguntaRequest(BaseModel):
    usuarioId: int
    partidaId: int
    preguntaId: int
    respuestaId: int
    tiempoRespuesta: int

class FinalizarPartidaRequest(BaseModel):
    usuarioId: int
    partidaId: int