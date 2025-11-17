from pydantic import BaseModel, Field
from typing import List, Optional

class UpdateProfileDto(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    edad: Optional[int] = None
    telefono: Optional[str] = None
    idioma: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    

class UpdateFotoPerfilDto(BaseModel):
    foto_perfil: str

class CreateDireccionDto(BaseModel):
    alias: str
    direccion_completa: str  # ← Cambio: antes era direccion_exacta
    ciudad: str              # ← Nuevo campo
    provincia: str
    codigo_postal: Optional[str] = None  # ← Nuevo campo
    latitud: Optional[float] = None      # ← Nuevo campo
    longitud: Optional[float] = None     # ← Nuevo campo
    referencia: Optional[str] = None     # ← Nuevo campo
    es_principal: bool = False

class CreateMetodoPagoDto(BaseModel):
    tipo: str  # 'tarjeta_credito', 'tarjeta_debito', 'efectivo', 'transferencia'
    alias: Optional[str] = None
    ultimos_digitos: Optional[str] = None
    marca: Optional[str] = None
    nombre_titular: Optional[str] = None
    fecha_expiracion: Optional[str] = None
    es_principal: bool = False
    token_pago: Optional[str] = None
    
class AddCondicionesSaludDto(BaseModel):
    condicion_ids: List[int]