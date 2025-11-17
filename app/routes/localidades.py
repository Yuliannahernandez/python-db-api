

from fastapi import APIRouter, HTTPException
from app.config.database import execute_query
from typing import Optional

router = APIRouter(
    prefix="/localidades",
    tags=["Localidades"]
)

@router.get("/paises")
def get_paises():
    """Obtener todos los países"""
    query = """
        SELECT id, descripcion 
        FROM localidades 
        WHERE nivel = 'pais' AND activo = TRUE
        ORDER BY descripcion ASC
    """
    return execute_query(query)

@router.get("/hijos/{padre_id}")
def get_hijos(padre_id: int):
    """Obtener localidades hijas de un padre"""
    query = """
        SELECT id, descripcion, nivel 
        FROM localidades 
        WHERE padre_id = %s AND activo = TRUE
        ORDER BY descripcion ASC
    """
    return execute_query(query, (padre_id,))

@router.get("/jerarquia/{localidad_id}")
def get_jerarquia(localidad_id: int):
    """Obtener la jerarquía completa de una localidad"""
    query = """
        WITH RECURSIVE jerarquia AS (
            SELECT id, descripcion, nivel, padre_id, 1 as profundidad
            FROM localidades
            WHERE id = %s
            
            UNION ALL
            
            SELECT l.id, l.descripcion, l.nivel, l.padre_id, j.profundidad + 1
            FROM localidades l
            INNER JOIN jerarquia j ON l.id = j.padre_id
        )
        SELECT * FROM jerarquia ORDER BY profundidad DESC
    """
    return execute_query(query, (localidad_id,))