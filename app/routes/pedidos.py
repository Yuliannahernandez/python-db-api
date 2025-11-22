from fastapi import APIRouter, HTTPException, Query,Request
from pydantic import BaseModel
from typing import Optional
from app.config.database import execute_query
from app.models.pedidos import CrearPedidoRequest, CancelarPedidoRequest

router = APIRouter(
    prefix="/pedidos",
    tags=["Pedidos"]
)

class ConfirmarPedidoDto(BaseModel):
    metodo_pago: str
    paypal_order_id: Optional[str] = None
    paypal_payer_id: Optional[str] = None
    paypal_amount: Optional[float] = None
    total: float

@router.post("/crear-desde-carrito")
async def crear_pedido_desde_carrito(request: Request):
    """Crear pedido desde el carrito"""
    
    body = await request.json()
    print(f"="*50)
    print(f" POST /pedidos/crear-desde-carrito")
    print(f" Body RAW recibido: {body}")
    print(f" Tipo de body: {type(body)}")
    print(f" Keys en body: {body.keys() if isinstance(body, dict) else 'No es dict'}")
    print(f"="*50)
    
    try:
        pedido_request = CrearPedidoRequest(**body)
        print(f" Parseado exitosamente")
        usuario_id = pedido_request.usuario_id
        print(f" usuario_id: {usuario_id}")
        metodo_pago = body.get('metodoPago', 'efectivo')
        paypal_order_id = body.get('paypalOrderId')
        paypal_payer_id = body.get('paypalPayerId')
        paypal_amount = body.get('paypalAmount')
        sinpe_comprobante = body.get('sinpeComprobante')
        sinpe_telefono = body.get('sinpeTelefono')
        print(f"metodo_pago: {metodo_pago}")
        print(f"PayPal Order ID: {paypal_order_id}")
    except Exception as e:
        print(f" Error parseando: {e}")
        raise HTTPException(status_code=422, detail=f"Error: {str(e)}")
    
    # 1. Buscar cliente
    print(f" Paso 1: Buscando cliente con usuario_id={usuario_id}")
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        print(f" Cliente no encontrado para usuario_id={usuario_id}")
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    print(f"Cliente encontrado: cliente_id={cliente_id}")
    
    # 2. Buscar carrito activo
    print(f" Paso 2: Buscando carrito activo para cliente_id={cliente_id}")
    carrito_query = """
        SELECT id, sucursal_id, metodo_pago_id 
        FROM pedidos 
        WHERE cliente_id = %s AND estado = 'carrito'
        ORDER BY fecha_creacion DESC 
        LIMIT 1
    """
    carrito = execute_query(carrito_query, (cliente_id,))
    
    if not carrito:
        print(f" No se encontró carrito activo para cliente_id={cliente_id}")
        raise HTTPException(status_code=404, detail="No hay carrito activo")
    
    carrito_id = carrito[0]['id']
    sucursal_id = carrito[0]['sucursal_id']
    metodo_pago_id = carrito[0]['metodo_pago_id']
    print(f"Carrito encontrado: carrito_id={carrito_id}, sucursal_id={sucursal_id}")
    
    # 3. Validar que tenga productos
    print(f" Paso 3: Validando productos en carrito")
    productos_query = "SELECT COUNT(*) as total FROM pedido_detalles WHERE pedido_id = %s"
    productos_count = execute_query(productos_query, (carrito_id,))
    
    if productos_count[0]['total'] == 0:
        print(f" El carrito está vacío")
        raise HTTPException(status_code=400, detail="El carrito está vacío")
    
    print(f" Carrito tiene {productos_count[0]['total']} productos")
    
    # 4. Validar sucursal
    if not sucursal_id:
        print(f" No hay sucursal seleccionada")
        raise HTTPException(status_code=400, detail="Debe seleccionar una sucursal")
    
    print(f" Sucursal validada: {sucursal_id}")
    
    # 5. Cambiar estado del carrito a 'pendiente'
    print(f" Paso 4: Cambiando estado del carrito a 'pendiente'")
    
    if metodo_pago == 'paypal' and paypal_order_id:
        update_query = """
            UPDATE pedidos 
            SET estado = 'pendiente',
                paypal_order_id = %s,
                paypal_payer_id = %s,
                paypal_amount = %s
            WHERE id = %s
        """
        execute_query(update_query, (paypal_order_id, paypal_payer_id, paypal_amount, carrito_id), fetch=False)
        print(f"Pedido con PayPal")
        
    elif metodo_pago == 'sinpe' and sinpe_comprobante:
        update_query = """
            UPDATE pedidos 
            SET estado = 'pendiente',
                sinpe_comprobante = %s,
                sinpe_telefono = %s,
                sinpe_verificado = FALSE
            WHERE id = %s
        """
        execute_query(update_query, (sinpe_comprobante, sinpe_telefono, carrito_id), fetch=False)
        print(f"🇨🇷 Pedido con SINPE - Comprobante: {sinpe_comprobante}")
        
    else:
        # Pago en efectivo
        update_query = """
            UPDATE pedidos 
            SET estado = 'confirmado',
                metodo_pago = 'efectivo',
                fecha_confirmacion = NOW()
            WHERE id = %s
        """
        execute_query(update_query, (carrito_id,), fetch=False)
        print(f"Pedido confirmado - Pago en efectivo")
    # 6. Retornar pedido creado
    print(f"Pedido creado exitosamente con ID: {carrito_id}")
    
    return {
        "id": carrito_id,
        "estado": "pendiente",
        "sucursal_id": sucursal_id,
        "metodo_pago_id": metodo_pago_id,
        "message": "Pedido creado exitosamente"
    }


@router.get("/activos")
def get_pedidos_activos():
    """Obtener pedidos activos (ADMIN)"""
    query = """
        SELECT 
            p.id,
            p.cliente_id,
            p.estado,
            p.tipo_entrega,
            p.total,
            p.tiempo_estimado,
            p.fecha_creacion,
            p.fecha_confirmacion,
            s.nombre as sucursal_nombre
        FROM pedidos p
        LEFT JOIN sucursales s ON p.sucursal_id = s.id
        WHERE p.estado IN ('confirmado', 'en_preparacion', 'listo')
        ORDER BY p.fecha_creacion ASC
    """
    pedidos = execute_query(query)
    
    # Obtener detalles de cada pedido
    for pedido in pedidos:
        detalles_query = """
            SELECT 
                pd.cantidad,
                pd.precio_unitario,
                pr.nombre
            FROM pedido_detalles pd
            JOIN productos pr ON pd.producto_id = pr.id
            WHERE pd.pedido_id = %s
        """
        detalles = execute_query(detalles_query, (pedido['id'],))
        
        pedido['productos'] = [
            {
                'nombre': d['nombre'],
                'cantidad': d['cantidad'],
                'precio': float(d['precio_unitario'])
            }
            for d in detalles
        ]
        pedido['sucursal'] = pedido.pop('sucursal_nombre')
        pedido['total'] = float(pedido['total'])
    
    return pedidos


@router.get("/usuario/{usuario_id}")
def get_pedidos_usuario(usuario_id: int):
    """Obtener pedidos de un usuario"""
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        return []
    
    cliente_id = cliente[0]['id']
    
    # Obtener pedidos con cantidad de productos
    query = """
        SELECT 
            p.id,
            p.estado,
            p.total,
            p.fecha_creacion,
            s.nombre as sucursal_nombre,
            (SELECT COUNT(*) FROM pedido_detalles WHERE pedido_id = p.id) as cantidad_productos
        FROM pedidos p
        LEFT JOIN sucursales s ON p.sucursal_id = s.id
        WHERE p.cliente_id = %s AND p.estado != 'carrito'
        ORDER BY p.fecha_creacion DESC
    """
    pedidos = execute_query(query, (cliente_id,))
    
    return [
        {
            "id": p['id'],
            "estado": p['estado'],
            "total": float(p['total']),
            "cantidad_productos": p['cantidad_productos'],
            "sucursal_nombre": p['sucursal_nombre'],
            "fecha_creacion": p['fecha_creacion'].isoformat() if p['fecha_creacion'] else None
        }
        for p in pedidos
    ]

@router.put("/{pedido_id}")
def actualizar_sucursal_pedido(
    pedido_id: int, 
    sucursal_id: int = Query(..., alias="sucursalId")
):
    """Asignar sucursal a un pedido (carrito)"""
    
    print(f" PUT recibido - Pedido: {pedido_id}, Sucursal: {sucursal_id}")
    
    try:
        # Verificar que el pedido existe
        pedido_query = "SELECT id, estado, sucursal_id FROM pedidos WHERE id = %s"
        pedido = execute_query(pedido_query, (pedido_id,))
        
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        
        print(f"Pedido encontrado - sucursal_id actual: {pedido[0].get('sucursal_id')}")
        
        # Verificar que la sucursal existe y está activa
        sucursal_query = "SELECT id, nombre FROM sucursales WHERE id = %s AND activa = TRUE"
        sucursal = execute_query(sucursal_query, (sucursal_id,))
        
        if not sucursal:
            raise HTTPException(status_code=404, detail="Sucursal no encontrada o inactiva")
        
        print(f" Sucursal válida: {sucursal[0]['nombre']}")
        
        # Actualizar el pedido con la sucursal
        update_query = "UPDATE pedidos SET sucursal_id = %s WHERE id = %s"
        execute_query(update_query, (sucursal_id, pedido_id), fetch=False)
        
        # VERIFICAR que se actualizó correctamente
        verify_query = "SELECT sucursal_id FROM pedidos WHERE id = %s"
        verify_result = execute_query(verify_query, (pedido_id,))
        
        nuevo_sucursal_id = verify_result[0]['sucursal_id'] if verify_result else None
        
        print(f" Después del UPDATE, sucursal_id = {nuevo_sucursal_id}")
        
        if nuevo_sucursal_id == sucursal_id:
            print(f"Actualización exitosa")
            return {
                "message": "Sucursal asignada exitosamente",
                "pedido_id": pedido_id,
                "sucursal_id": sucursal_id,
                "sucursal_nombre": sucursal[0]['nombre']
            }
        else:
            print(f" La actualización falló - valor esperado: {sucursal_id}, valor actual: {nuevo_sucursal_id}")
            raise HTTPException(status_code=500, detail="No se pudo actualizar el pedido")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f" Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    


@router.get("/{pedido_id}/detalle")
def get_pedido_detalle(pedido_id: int):
    """Obtener detalle del pedido"""
    
    print(f" Obteniendo detalle del pedido {pedido_id}")
    
    try:
        # Obtener pedido con toda la información
        pedido_query = """
            SELECT 
                p.*,
                s.nombre as sucursal_nombre,
                s.direccion as sucursal_direccion,
                s.provincia as sucursal_provincia,
                s.telefono as sucursal_telefono,
                c.nombre as cliente_nombre,
                c.telefono as cliente_telefono
            FROM pedidos p
            LEFT JOIN sucursales s ON p.sucursal_id = s.id
            LEFT JOIN clientes c ON p.cliente_id = c.id
            WHERE p.id = %s
        """
        
        pedido = execute_query(pedido_query, (pedido_id,))
        
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        
        pedido_data = pedido[0]
        
        # Obtener productos del pedido
        productos_query = """
            SELECT 
                pd.id,
                pd.producto_id,
                pd.cantidad,
                pd.precio_unitario,
                pd.subtotal,
                pr.nombre,
                pr.descripcion,
                pr.imagen_principal as imagen
            FROM pedido_detalles pd
            JOIN productos pr ON pd.producto_id = pr.id
            WHERE pd.pedido_id = %s
        """
        
        productos = execute_query(productos_query, (pedido_id,))
        
        # Construir respuesta
        sucursal_obj = None
        if pedido_data.get('sucursal_id'):
            sucursal_obj = {
                "id": pedido_data['sucursal_id'],
                "nombre": pedido_data['sucursal_nombre'],
                "direccion": pedido_data['sucursal_direccion'],
                "provincia": pedido_data['sucursal_provincia'],
                "telefono": pedido_data['sucursal_telefono']
            }
        
        return {
            "id": pedido_data['id'],
            "estado": pedido_data['estado'],
            "subtotal": float(pedido_data['subtotal']),
            "descuento": float(pedido_data['descuento']),
            "costoEnvio": float(pedido_data['costo_envio']),
            "total": float(pedido_data['total']),
            "sucursal": sucursal_obj,
            "productos": [
                {
                    "id": p['id'],
                    "productoId": p['producto_id'],
                    "nombre": p['nombre'],
                    "descripcion": p['descripcion'],
                    "imagen": p['imagen'],
                    "precio": float(p['precio_unitario']),
                    "cantidad": p['cantidad'],
                    "subtotal": float(p['subtotal'])
                }
                for p in productos
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error obteniendo pedido: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{pedido_id}/cancelar")
def cancelar_pedido(pedido_id: int, request: CancelarPedidoRequest):
    """Cancelar un pedido"""
    usuario_id = request.usuario_id
    
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Buscar pedido
    pedido_query = """
        SELECT * FROM pedidos 
        WHERE id = %s AND cliente_id = %s
    """
    pedido = execute_query(pedido_query, (pedido_id, cliente_id))
    
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    pedido = pedido[0]
    
    # Validar estado
    if pedido['estado'] in ['completado', 'cancelado']:
        raise HTTPException(status_code=400, detail="No se puede cancelar este pedido")
    
    # Cancelar pedido
    update_query = "UPDATE pedidos SET estado = 'cancelado' WHERE id = %s"
    execute_query(update_query, (pedido_id,), fetch=False)
    
    return {
        "message": "Pedido cancelado exitosamente",
        "id": pedido_id,
        "estado": "cancelado"
    }


@router.put("/{pedido_id}/estado")
def cambiar_estado_pedido(pedido_id: int, estado: str = Query(...)):
    """Cambiar estado de un pedido (ADMIN)"""
    estados_validos = ['confirmado', 'en_preparacion', 'listo', 'completado', 'cancelado']
    
    if estado not in estados_validos:
        raise HTTPException(status_code=400, detail="Estado no válido")
    
    # Obtener pedido actual
    pedido_query = "SELECT estado FROM pedidos WHERE id = %s"
    pedido = execute_query(pedido_query, (pedido_id,))
    
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    estado_actual = pedido[0]['estado']
    
    # No permitir cambiar pedidos completados o cancelados
    if estado_actual in ['completado', 'cancelado']:
        raise HTTPException(
            status_code=400,
            detail="No se puede cambiar el estado de este pedido"
        )
    
    # Actualizar estado
    update_query = "UPDATE pedidos SET estado = %s"
    params = [estado]
    
    # Si se completa, agregar fecha
    if estado == 'completado':
        update_query += ", fecha_completado = NOW()"
    
    update_query += " WHERE id = %s"
    params.append(pedido_id)
    
    execute_query(update_query, tuple(params), fetch=False)
    
    return {
        "id": pedido_id,
        "estado": estado,
        "mensaje": f"Pedido actualizado a: {estado}"
    }