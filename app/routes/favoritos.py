from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from app.config.database import execute_query

router = APIRouter(
    prefix="/favoritos",
    tags=["Favoritos"]
)

class AgregarFavoritoRequest(BaseModel):
    producto_id: int

@router.get("/mis-favoritos")
async def obtener_favoritos(usuario_id: int = Header(..., alias="usuario-id")):
    """Obtener todos los favoritos de un usuario"""
    
    try:
        print(f"Obteniendo favoritos para usuario_id: {usuario_id}")
        
        # 1. Buscar cliente
        cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
        cliente = execute_query(cliente_query, (usuario_id,))
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        cliente_id = cliente[0]['id']
        
        # 2. Obtener favoritos con información del producto
        favoritos_query = """
            SELECT 
                f.id as favorito_id,
                f.fecha_agregado,
                p.id as producto_id,
                p.nombre,
                p.descripcion,
                p.precio,
                p.imagen_principal,
                p.categoria,
                p.es_nuevo
            FROM favoritos f
            JOIN productos p ON f.producto_id = p.id
            WHERE f.cliente_id = %s
            ORDER BY f.fecha_agregado DESC
        """
        
        favoritos = execute_query(favoritos_query, (cliente_id,))
        
        return {
            "favoritos": [
                {
                    "favoritoId": fav['favorito_id'],
                    "fechaAgregado": fav['fecha_agregado'].isoformat() if fav['fecha_agregado'] else None,
                    "producto": {
                        "id": fav['producto_id'],
                        "nombre": fav['nombre'],
                        "descripcion": fav['descripcion'],
                        "precio": float(fav['precio']),
                        "imagenPrincipal": fav['imagen_principal'],
                        "categoria": fav['categoria'],
                        "esNuevo": fav['es_nuevo']
                    }
                }
                for fav in favoritos
            ],
            "total": len(favoritos)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error obteniendo favoritos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/toggle/{producto_id}")
async def toggle_favorito(
    producto_id: int,
    usuario_id: int = Header(..., alias="usuario-id")
):
    """Toggle favorito (agregar si no existe, eliminar si existe) - VERSIÓN MYSQL"""
    
    try:
        print(f"Toggle favorito - Usuario: {usuario_id}, Producto: {producto_id}")
        
        # 1. Buscar cliente
        cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
        cliente = execute_query(cliente_query, (usuario_id,))
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        cliente_id = cliente[0]['id']
        print(f"Cliente encontrado: cliente_id={cliente_id}")
        
        # 2. Verificar si existe
        existe_query = """
            SELECT id, fecha_agregado FROM favoritos 
            WHERE cliente_id = %s AND producto_id = %s
        """
        existe = execute_query(existe_query, (cliente_id, producto_id))
        
        if existe:
            # ELIMINAR favorito
            favorito_id = existe[0]['id']
            
            delete_query = """
                DELETE FROM favoritos 
                WHERE cliente_id = %s AND producto_id = %s
            """
            execute_query(delete_query, (cliente_id, producto_id), fetch=False)
            
            print(f"Favorito eliminado exitosamente")
            return {
                "message": "Producto eliminado de favoritos",
                "esFavorito": False,
                "accion": "eliminado"
            }
        else:
            
            # Verificar que el producto existe
            producto_query = "SELECT id, nombre FROM productos WHERE id = %s"
            producto = execute_query(producto_query, (producto_id,))
            
            if not producto:
                raise HTTPException(status_code=404, detail="Producto no encontrado")
            
            
            insert_query = """
                INSERT INTO favoritos (cliente_id, producto_id, fecha_agregado)
                VALUES (%s, %s, NOW())
            """
            execute_query(insert_query, (cliente_id, producto_id), fetch=False)
            
            favorito_query = """
                SELECT id, fecha_agregado 
                FROM favoritos 
                WHERE cliente_id = %s AND producto_id = %s
            """
            favorito_resultado = execute_query(favorito_query, (cliente_id, producto_id))
            
            if favorito_resultado:
                favorito_id = favorito_resultado[0]['id']
                fecha_agregado = favorito_resultado[0]['fecha_agregado']
                fecha_iso = fecha_agregado.isoformat() if fecha_agregado else None
            else:
               
                favorito_id = None
                fecha_iso = None
            
            print(f"Favorito agregado exitosamente con ID: {favorito_id}")
            return {
                "message": f"{producto[0]['nombre']} agregado a favoritos",
                "esFavorito": True,
                "accion": "agregado",
                "favoritoId": favorito_id,
                "fechaAgregado": fecha_iso
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en toggle favorito: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/es-favorito/{producto_id}")
async def verificar_favorito(
    producto_id: int,
    usuario_id: int = Header(..., alias="usuario-id")
):
    """Verificar si un producto está en favoritos"""
    
    try:
        # 1. Buscar cliente
        cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
        cliente = execute_query(cliente_query, (usuario_id,))
        
        if not cliente:
            return {"esFavorito": False}
        
        cliente_id = cliente[0]['id']
        
        # 2. Verificar favorito
        existe_query = """
            SELECT id FROM favoritos 
            WHERE cliente_id = %s AND producto_id = %s
        """
        existe = execute_query(existe_query, (cliente_id, producto_id))
        
        return {
            "esFavorito": len(existe) > 0,
            "favoritoId": existe[0]['id'] if existe else None
        }
        
    except Exception as e:
        print(f"Error verificando favorito: {e}")
        return {"esFavorito": False}


@router.post("/agregar")
async def agregar_favorito(
    request: AgregarFavoritoRequest,
    usuario_id: int = Header(..., alias="usuario-id")
):
    """Agregar un producto a favoritos"""
    
    try:
        print(f"Agregando favorito - Usuario: {usuario_id}, Producto: {request.producto_id}")
        
        # 1. Buscar cliente
        cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
        cliente = execute_query(cliente_query, (usuario_id,))
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        cliente_id = cliente[0]['id']
        
        # 2. Verificar que el producto existe
        producto_query = "SELECT id, nombre FROM productos WHERE id = %s"
        producto = execute_query(producto_query, (request.producto_id,))
        
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        # 3. Verificar si ya está en favoritos
        existe_query = """
            SELECT id FROM favoritos 
            WHERE cliente_id = %s AND producto_id = %s
        """
        existe = execute_query(existe_query, (cliente_id, request.producto_id))
        
        if existe:
            return {
                "message": "El producto ya está en favoritos",
                "yaExiste": True,
                "favoritoId": existe[0]['id']
            }
        
        # 4. Agregar a favoritos 
        insert_query = """
            INSERT INTO favoritos (cliente_id, producto_id, fecha_agregado)
            VALUES (%s, %s, NOW())
        """
        execute_query(insert_query, (cliente_id, request.producto_id), fetch=False)
        
        # 5. Obtener el registro insertado
        favorito_query = """
            SELECT id, fecha_agregado 
            FROM favoritos 
            WHERE cliente_id = %s AND producto_id = %s
        """
        favorito_resultado = execute_query(favorito_query, (cliente_id, request.producto_id))
        
        if favorito_resultado:
            favorito_id = favorito_resultado[0]['id']
            fecha_agregado = favorito_resultado[0]['fecha_agregado']
        else:
            # Fallback
            favorito_id = None
            fecha_agregado = None
        
        print(f"Favorito agregado exitosamente")
        
        return {
            "message": f"{producto[0]['nombre']} agregado a favoritos",
            "favoritoId": favorito_id,
            "fechaAgregado": fecha_agregado.isoformat() if fecha_agregado else None,
            "yaExiste": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error agregando favorito: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
@router.delete("/eliminar/{producto_id}")
async def eliminar_favorito(
    producto_id: int,
    usuario_id: int = Header(..., alias="usuario-id")
):
    """Eliminar un producto de favoritos"""
    
    try:
        print(f"Eliminando favorito - Usuario: {usuario_id}, Producto: {producto_id}")
        
        # 1. Buscar cliente
        cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
        cliente = execute_query(cliente_query, (usuario_id,))
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        cliente_id = cliente[0]['id']
        
        # 2. Verificar que existe antes de eliminar
        existe_query = """
            SELECT id FROM favoritos 
            WHERE cliente_id = %s AND producto_id = %s
        """
        existe = execute_query(existe_query, (cliente_id, producto_id))
        
        if not existe:
            raise HTTPException(status_code=404, detail="Favorito no encontrado")
        
        favorito_id = existe[0]['id']
        
        # 3. Eliminar favorito
        delete_query = """
            DELETE FROM favoritos 
            WHERE cliente_id = %s AND producto_id = %s
        """
        execute_query(delete_query, (cliente_id, producto_id), fetch=False)
        
        print(f"Favorito eliminado exitosamente")
        
        return {
            "message": "Producto eliminado de favoritos",
            "favoritoId": favorito_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error eliminando favorito: {e}")
        raise HTTPException(status_code=500, detail=str(e))