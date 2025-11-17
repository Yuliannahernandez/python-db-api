from fastapi import APIRouter, HTTPException
from app.config.database import execute_query  # Asegúrate de tener la función en tu módulo de conexión

router = APIRouter(
    prefix="/categorias",
    tags=["Categorias"]
)

# ============= OBTENER TODAS LAS CATEGORÍAS =============
@router.get("/")
def get_categorias():
    query = "SELECT * FROM categorias ORDER BY nombre ASC"
    result = execute_query(query)
    return result

# ============= OBTENER UNA CATEGORÍA POR ID =============
@router.get("/{id}")
def get_categoria(id: int):
    query = "SELECT * FROM categorias WHERE id = %s"
    result = execute_query(query, (id,))
    if not result:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return result[0]

# ============= PRODUCTOS DE UNA CATEGORÍA =============
@router.get("/{id}/productos")
def get_productos_categoria(id: int):
    query = """
        SELECT 
            p.*, 
            c.nombre AS categoria_nombre
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.categoria_id = %s AND p.disponible = TRUE
        ORDER BY p.en_tendencia DESC, p.es_nuevo DESC, p.nombre ASC
    """
    result = execute_query(query, (id,))
    if not result:
        raise HTTPException(status_code=404, detail="No se encontraron productos para esta categoría")
    return result
