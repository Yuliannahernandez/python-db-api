
from fastapi import APIRouter, HTTPException

from app.config.database import execute_query
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/productos", tags=["Productos"])

class CrearProductoDto(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: float
    categoriaId: int = Field(alias='categoriaId') 
    imagenPrincipal: Optional[str] = Field(None, alias='imagenPrincipal')
    disponible: bool = True
    tiempoPreparacion: int = Field(15, alias='tiempoPreparacion')
class Config:
        populate_by_name = True 


@router.get("/")
def get_productos():
    query = """
        SELECT p.*, c.nombre as categoria_nombre
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.disponible = TRUE
        ORDER BY p.fecha_creacion DESC
    """
    return execute_query(query)

@router.get("/{id}")
def get_producto(id: int):
    query = """
        SELECT p.*, c.nombre as categoria_nombre
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.id = %s
    """
    result = execute_query(query, (id,))
    if not result:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return result[0]

@router.get("/{id}/detalle")
def get_producto_detalle_completo(id: int):
    
    producto_query = """
        SELECT 
            p.*, 
            c.nombre AS categoria_nombre
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.id = %s AND p.disponible = TRUE
    """
    producto = execute_query(producto_query, (id,))
    
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    producto = producto[0]
    
    # Ingredientes
    ingredientes_query = """
        SELECT 
            i.nombre,
            pi.cantidad,
            i.es_alergeno
        FROM producto_ingredientes pi
        JOIN ingredientes i ON pi.ingrediente_id = i.id
        WHERE pi.producto_id = %s
    """
    ingredientes = execute_query(ingredientes_query, (id,))
    
    # Información nutricional
    nutri_query = """
        SELECT * 
        FROM informacion_nutricional
        WHERE producto_id = %s
    """
    nutri = execute_query(nutri_query, (id,))
    
    # Imágenes
    imagenes_query = """
        SELECT url_imagen
        FROM producto_imagenes
        WHERE producto_id = %s
        ORDER BY orden ASC
    """
    imagenes = execute_query(imagenes_query, (id,))
    
    return {
        **producto,
        "imagenes": [img['url_imagen'] for img in imagenes],
        "ingredientes": ingredientes,
        "informacion_nutricional": nutri[0] if nutri else None
    }

@router.post("/")
def crear_producto(producto: CrearProductoDto):
    """Crear un nuevo producto"""
    
    print(f"Creando producto: {producto.nombre}")
    print(f"Datos recibidos: categoriaId={producto.categoriaId}, precio={producto.precio}")
    
    try:
        # Verificar que la categoría existe
        cat_query = "SELECT id FROM categorias WHERE id = %s"
        categoria = execute_query(cat_query, (producto.categoriaId,)) 
        
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        
        # Insertar producto
        query = """
            INSERT INTO productos 
            (nombre, descripcion, precio, categoria_id, imagen_principal, disponible, tiempo_preparacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        result = execute_query(
            query,
            (
                producto.nombre,
                producto.descripcion,
                producto.precio,
                producto.categoriaId,       
                producto.imagenPrincipal,    
                producto.disponible,
                producto.tiempoPreparacion   
            ),
            fetch=False
        )
        
        producto_id = result['last_id']
        
        print(f" Producto creado con ID: {producto_id}")
        
        return {
            "id": producto_id,
            "nombre": producto.nombre,
            "precio": producto.precio,
            "message": "Producto creado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f" Error creando producto: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{producto_id}")
def actualizar_producto(producto_id: int, producto: CrearProductoDto):
    """Actualizar un producto existente"""
    
    print(f" Actualizando producto {producto_id}")
    
    try:
        # Verificar que el producto existe
        check_query = "SELECT id FROM productos WHERE id = %s"
        existe = execute_query(check_query, (producto_id,))
        
        if not existe:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        # Actualizar producto
        query = """
            UPDATE productos 
            SET nombre = %s,
                descripcion = %s,
                precio = %s,
                categoria_id = %s,
                imagen_principal = %s,
                disponible = %s,
                tiempo_preparacion = %s
            WHERE id = %s
        """
        
        execute_query(
            query,
            (
                producto.nombre,
                producto.descripcion,
                producto.precio,
                producto.categoria_id,
                producto.imagen_principal,
                producto.disponible,
                producto.tiempo_preparacion,
                producto_id
            ),
            fetch=False
        )
        
        print(f"Producto actualizado")
        
        return {
            "id": producto_id,
            "message": "Producto actualizado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error actualizando producto: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{producto_id}")
def eliminar_producto(producto_id: int):
    """Eliminar un producto (soft delete)"""
    
    print(f"Eliminando producto {producto_id}")
    
    try:
        # Marcar como no disponible en lugar de eliminar
        query = "UPDATE productos SET disponible = FALSE WHERE id = %s"
        result = execute_query(query, (producto_id,), fetch=False)
        
        if result.get('affected_rows', 0) == 0:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        print(f" Producto eliminado")
        
        return {"message": "Producto eliminado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f" Error eliminando producto: {e}")
        raise HTTPException(status_code=500, detail=str(e))