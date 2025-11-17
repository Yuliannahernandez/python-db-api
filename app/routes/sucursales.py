from fastapi import APIRouter, HTTPException
from app.config.database import execute_query

router = APIRouter(
    prefix="/sucursales",
    tags=["Sucursales"]
)

# ============= SUCURSALES =============
@router.get("/") 
def get_sucursales():
    """Obtener todas las sucursales activas"""
    query = "SELECT * FROM sucursales WHERE activa = TRUE ORDER BY orden ASC"
    return execute_query(query)

@router.get("/{id}")  
def get_sucursal(id: int):
    """Obtener una sucursal por ID"""
    query = "SELECT * FROM sucursales WHERE id = %s AND activa = TRUE"
    result = execute_query(query, (id,))
    
    if not result:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    
    return result[0]