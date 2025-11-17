from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config.database import execute_query

router = APIRouter(
    prefix="/carrito",
    tags=["Carrito"]
)

class AgregarProductoDto(BaseModel):
    producto_id: int
    cantidad: int = 1
# ============= CARRITO =============
# routes/carrito.py

@router.get("/usuario/{usuario_id}")
def get_carrito(usuario_id: int):
    """Obtener carrito activo del usuario"""
    
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Buscar carrito activo CON SUCURSAL
    carrito_query = """
        SELECT 
            p.*,
            s.id as sucursal_id,
            s.nombre as sucursal_nombre,
            s.direccion as sucursal_direccion,
            s.provincia as sucursal_provincia,
            s.telefono as sucursal_telefono,
            s.horario as sucursal_horario
        FROM pedidos p
        LEFT JOIN sucursales s ON p.sucursal_id = s.id
        WHERE p.cliente_id = %s AND p.estado = 'carrito'
        ORDER BY p.fecha_creacion DESC
        LIMIT 1
    """
    
    carrito = execute_query(carrito_query, (cliente_id,))
    
    if not carrito:
        # Crear carrito vacío si no existe
        insert_query = """
            INSERT INTO pedidos (cliente_id, estado, subtotal, descuento, costo_envio, total)
            VALUES (%s, 'carrito', 0, 0, 0, 0)
        """
        result = execute_query(insert_query, (cliente_id,), fetch=False)
        pedido_id = result['last_id']
        
        return {
            "id": pedido_id,
            "subtotal": 0,
            "descuento": 0,
            "costoEnvio": 0,
            "total": 0,
            "tiempoEstimado": 0,
            "productos": [],
            "sucursal": None,
            "sucursal_id": None
        }
    
    carrito = carrito[0]
    pedido_id = carrito['id']
    
    # Obtener productos del carrito
    productos_query = """
        SELECT 
            pd.id,
            pd.producto_id,
            pd.cantidad,
            pd.precio_unitario,
            pd.subtotal,
            pd.notas_especiales,
            pr.nombre,
            pr.descripcion,
            pr.imagen_principal as imagen
        FROM pedido_detalles pd
        JOIN productos pr ON pd.producto_id = pr.id
        WHERE pd.pedido_id = %s
    """
    
    productos = execute_query(productos_query, (pedido_id,))
    
    # Calcular tiempo estimado
    if productos:
        tiempo_query = """
            SELECT MAX(pr.tiempo_preparacion) as max_tiempo
            FROM pedido_detalles pd
            JOIN productos pr ON pd.producto_id = pr.id
            WHERE pd.pedido_id = %s
        """
        tiempo_result = execute_query(tiempo_query, (pedido_id,))
        tiempo_estimado = tiempo_result[0]['max_tiempo'] or 15
    else:
        tiempo_estimado = 0
    
    # Construir objeto de sucursal si existe
    sucursal_obj = None
    if carrito.get('sucursal_id'):
        sucursal_obj = {
            "id": carrito['sucursal_id'],
            "nombre": carrito['sucursal_nombre'],
            "direccion": carrito['sucursal_direccion'],
            "provincia": carrito['sucursal_provincia'],
            "telefono": carrito['sucursal_telefono'],
            "horario": carrito['sucursal_horario']
        }
    
    return {
        "id": carrito['id'],
        "subtotal": float(carrito['subtotal']),
        "descuento": float(carrito['descuento']),
        "costoEnvio": float(carrito['costo_envio']),
        "total": float(carrito['total']),
        "tiempoEstimado": tiempo_estimado,
        "productos": [
            {
                "id": p['id'],
                "productoId": p['producto_id'],
                "nombre": p['nombre'],
                "descripcion": p['descripcion'],
                "imagen": p['imagen'],
                "precio": float(p['precio_unitario']),
                "cantidad": p['cantidad'],
                "subtotal": float(p['subtotal']),
                "notas": p['notas_especiales']
            }
            for p in productos
        ],
        "sucursal": sucursal_obj, 
        "sucursal_id": carrito.get('sucursal_id') 
    }
    
    # routes/carrito.py

@router.post("/usuario/{usuario_id}/agregar")
def agregar_producto_al_carrito(usuario_id: int, data: AgregarProductoDto):
    """Agregar producto al carrito del usuario"""
    
    producto_id = data.producto_id  
    cantidad = data.cantidad        
    
    print(f" Agregando producto {producto_id} (cant: {cantidad}) para usuario {usuario_id}")
    
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Buscar o crear carrito activo
    carrito_query = """
        SELECT id FROM pedidos 
        WHERE cliente_id = %s AND estado = 'carrito'
        ORDER BY fecha_creacion DESC
        LIMIT 1
    """
    carrito = execute_query(carrito_query, (cliente_id,))
    
    if not carrito:
        # Crear carrito nuevo
        insert_carrito = """
            INSERT INTO pedidos (cliente_id, estado, tipo_entrega, subtotal, descuento, costo_envio, total)
            VALUES (%s, 'carrito', 'recoger_tienda', 0, 0, 0, 0)
        """
        result = execute_query(insert_carrito, (cliente_id,), fetch=False)
        carrito_id = result['last_id']
    else:
        carrito_id = carrito[0]['id']
    
    # Verificar que el producto existe y obtener su precio
    producto_query = "SELECT id, precio, disponible FROM productos WHERE id = %s"
    producto = execute_query(producto_query, (producto_id,))
    
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    if not producto[0]['disponible']:
        raise HTTPException(status_code=400, detail="Producto no disponible")
    
    precio = float(producto[0]['precio'])
    
    # Verificar si el producto ya está en el carrito
    check_query = """
        SELECT id, cantidad FROM pedido_detalles 
        WHERE pedido_id = %s AND producto_id = %s
    """
    existing = execute_query(check_query, (carrito_id, producto_id))
    
    if existing:
        # Actualizar cantidad existente
        nueva_cantidad = existing[0]['cantidad'] + cantidad
        subtotal = nueva_cantidad * precio
        
        update_query = """
            UPDATE pedido_detalles 
            SET cantidad = %s, subtotal = %s 
            WHERE id = %s
        """
        execute_query(update_query, (nueva_cantidad, subtotal, existing[0]['id']), fetch=False)
        print(f" Cantidad actualizada a {nueva_cantidad}")
    else:
        # Insertar nuevo producto
        subtotal = cantidad * precio
        
        insert_query = """
            INSERT INTO pedido_detalles 
            (pedido_id, producto_id, cantidad, precio_unitario, subtotal)
            VALUES (%s, %s, %s, %s, %s)
        """
        execute_query(insert_query, (carrito_id, producto_id, cantidad, precio, subtotal), fetch=False)
        print(f" Producto agregado")
    
    # Recalcular totales del carrito
    recalcular_carrito(carrito_id)
    
    return {
        "message": "Producto agregado al carrito exitosamente",
        "carrito_id": carrito_id,
        "producto_id": producto_id,
        "cantidad": cantidad
    }

# ... resto de endpoints existentes

@router.post("/")
def create_carrito(usuario_id: int):
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s" 
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Crear pedido con estado 'carrito'
    query = """
        INSERT INTO pedidos (cliente_id, estado, tipo_entrega, subtotal, descuento, costo_envio, total)
        VALUES (%s, 'carrito', 'domicilio', 0, 0, 0, 0)
    """  
    result = execute_query(query, (cliente_id,), fetch=False)
    return {"id": result['last_id'], "clienteId": cliente_id}

@router.post("/items")
def add_carrito_item(carritoId: int, productoId: int, cantidad: int):
    # Verificar si el producto ya existe en el carrito
    check_query = "SELECT id, cantidad FROM pedido_detalles WHERE pedido_id = %s AND producto_id = %s"  
    existing = execute_query(check_query, (carritoId, productoId))
    
    # Obtener precio del producto
    precio_query = "SELECT precio FROM productos WHERE id = %s"
    producto = execute_query(precio_query, (productoId,))
    
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    precio = producto[0]['precio']
    
    if existing:
        # Actualizar cantidad
        nueva_cantidad = existing[0]['cantidad'] + cantidad
        subtotal = nueva_cantidad * precio
        update_query = """
            UPDATE pedido_detalles 
            SET cantidad = %s, subtotal = %s 
            WHERE id = %s
        """
        execute_query(update_query, (nueva_cantidad, subtotal, existing[0]['id']), fetch=False)
    else:
        
        subtotal = cantidad * precio
        insert_query = """
            INSERT INTO pedido_detalles (pedido_id, producto_id, cantidad, precio_unitario, subtotal)
            VALUES (%s, %s, %s, %s, %s)
        """  
        execute_query(insert_query, (carritoId, productoId, cantidad, precio, subtotal), fetch=False)
    
    # Recalcular totales del carrito
    recalcular_carrito(carritoId)
    
    return {"message": "Item agregado al carrito"}

def recalcular_carrito(carrito_id: int):
    """Recalcula subtotal y total del carrito"""
    query = "SELECT SUM(subtotal) as total FROM pedido_detalles WHERE pedido_id = %s"  # ✅ snake_case
    result = execute_query(query, (carrito_id,))
    
    subtotal = result[0]['total'] or 0
    
    # Obtener descuento actual
    pedido_query = "SELECT descuento, tipo_entrega FROM pedidos WHERE id = %s"  # ✅ snake_case
    pedido = execute_query(pedido_query, (carrito_id,))
    
    descuento = pedido[0]['descuento'] or 0
    tipo_entrega = pedido[0]['tipo_entrega']  # ✅ snake_case
    
    # Calcular costo de envío
    costo_envio = 0
    if tipo_entrega == 'domicilio':
        costo_envio = 0 if subtotal > 10000 else 1500
    
    total = subtotal - descuento + costo_envio
    
    # Actualizar pedido
    update_query = """
        UPDATE pedidos 
        SET subtotal = %s, costo_envio = %s, total = %s 
        WHERE id = %s
    """  
    execute_query(update_query, (subtotal, costo_envio, total, carrito_id), fetch=False)

@router.delete("/items/{id}")
def delete_carrito_item(id: int):
    # Obtener el pedidoId antes de eliminar
    query = "SELECT pedido_id FROM pedido_detalles WHERE id = %s" 
    result = execute_query(query, (id,))
    
    if not result:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    
    pedido_id = result[0]['pedido_id'] 
    
    # Eliminar item
    execute_query("DELETE FROM pedido_detalles WHERE id = %s", (id,), fetch=False)
    
    # Recalcular totales
    recalcular_carrito(pedido_id)
    
    return {"message": "Item eliminado del carrito"}

@router.delete("/vaciar/{carrito_id}")
def vaciar_carrito(carrito_id: int):
    execute_query("DELETE FROM pedido_detalles WHERE pedido_id = %s", (carrito_id,), fetch=False)  
    
    # Resetear totales
    execute_query("""
        UPDATE pedidos 
        SET subtotal = 0, descuento = 0, costo_envio = 0, total = 0 
        WHERE id = %s
    """, (carrito_id,), fetch=False)  
    
    return {"message": "Carrito vaciado"}
