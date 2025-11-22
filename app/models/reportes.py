from pydantic import BaseModel
from typing import Optional

class ReporteVentasRequest(BaseModel):
    fechaInicio: Optional[str] = None
    fechaFin: Optional[str] = None