from fastapi import APIRouter, HTTPException
from app.config.database import execute_query
from app.models.cupones import CuponValidarRequest, CuponAplicarRequest, CuponUsoRequest
from datetime import date

router = APIRouter(
    prefix="/cupones",
    tags=["Cupones"]
)

# ============= OBTENER TODOS LOS CUPONES =============
@router.get("/")
def get_cupones():
    """Obtener todos los cupones activos"""
    return execute_query("SELECT * FROM cupones WHERE activo = TRUE")

# ============= OBTENER CUPÓN POR CÓDIGO =============
@router.get("/codigo/{codigo}")
def get_cupon_by_codigo(codigo: str):
    """Obtener cupón por código"""
    
    query = """
        SELECT * FROM cupones 
        WHERE UPPER(codigo) = UPPER(%s) AND activo = TRUE 
        AND fecha_inicio <= CURDATE() AND fecha_fin >= CURDATE()
    """
    result = execute_query(query, (codigo,))
    
    if not result:
        raise HTTPException(status_code=404, detail="Cupón no válido o expirado")
    
    return result[0]

# ============= VALIDAR CUPÓN =============
@router.post("/validar")
def validar_cupon(request: CuponValidarRequest):
    """Validar si un cupón es válido para un usuario"""
    
    codigo = request.codigo.upper()
    usuario_id = request.usuarioId
    
    print(f"Validando cupón: {codigo} para usuario {usuario_id}")
    
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Buscar cupón
    cupon_query = """
        SELECT * FROM cupones 
        WHERE UPPER(codigo) = UPPER(%s) AND activo = TRUE 
        AND fecha_inicio <= CURDATE() AND fecha_fin >= CURDATE()
    """
    cupon = execute_query(cupon_query, (codigo,))
    
    if not cupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado o inactivo")
    
    cupon = cupon[0]
    
    # Validar fechas
    hoy = date.today()
    
    if cupon['fecha_inicio'] > hoy:
        raise HTTPException(status_code=400, detail="El cupón aún no está disponible")
    
    if cupon['fecha_fin'] < hoy:
        raise HTTPException(status_code=400, detail="El cupón ha expirado")
    
    # Validar usos totales
    if cupon['usos_maximos']:
        usos_query = "SELECT COUNT(*) as total FROM cupon_usos WHERE cupon_id = %s"
        usos = execute_query(usos_query, (cupon['id'],))
        usos_actuales = usos[0]['total']
        
        if usos_actuales >= cupon['usos_maximos']:
            raise HTTPException(status_code=400, detail="El cupón ha alcanzado su límite de usos")
    
    # Validar usos por cliente
    usos_cliente_query = """
        SELECT COUNT(*) as total 
        FROM cupon_usos 
        WHERE cupon_id = %s AND cliente_id = %s
    """
    usos_cliente = execute_query(usos_cliente_query, (cupon['id'], cliente_id))
    usos_cliente_total = usos_cliente[0]['total']
    
    if usos_cliente_total >= cupon['usos_por_cliente']:
        raise HTTPException(status_code=400, detail="Ya has usado este cupón el máximo de veces permitido")
    
    print(f" Cupón válido")
    
    return {
        "valido": True,
        "cupon": {
            "codigo": cupon['codigo'],
            "descripcion": cupon['descripcion'],
            "tipoDescuento": cupon['tipo_descuento'],
            "valorDescuento": float(cupon['valor_descuento']),
            "montoMinimo": float(cupon['monto_minimo']),
        }
    }

# ============= APLICAR CUPÓN AL CARRITO =============
@router.post("/aplicar")
def aplicar_cupon(request: CuponAplicarRequest):
    """Aplicar cupón al carrito del usuario"""
    
    codigo = request.codigo.upper()
    usuario_id = request.usuarioId
    
    print(f" Aplicando cupón {codigo} para usuario {usuario_id}")
    
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Validar cupón primero
    try:
        validacion = validar_cupon(CuponValidarRequest(codigo=codigo, usuarioId=usuario_id))
    except HTTPException as e:
        raise e
    
    # Buscar carrito
    carrito_query = """
        SELECT * FROM pedidos 
        WHERE cliente_id = %s AND estado = 'carrito'
    """
    carrito = execute_query(carrito_query, (cliente_id,))
    
    if not carrito:
        raise HTTPException(status_code=404, detail="No tienes un carrito activo")
    
    carrito = carrito[0]
    
    # Buscar cupón completo
    cupon_query = "SELECT * FROM cupones WHERE UPPER(codigo) = UPPER(%s)"
    cupon = execute_query(cupon_query, (codigo,))
    cupon = cupon[0]
    
    # Validar monto mínimo
    subtotal = float(carrito['subtotal'])
    monto_minimo = float(cupon['monto_minimo'])
    
    if subtotal < monto_minimo:
        raise HTTPException(
            status_code=400,
            detail=f"El monto mínimo para usar este cupón es ₡{int(monto_minimo):,}"
        )
    
    # Calcular descuento
    if cupon['tipo_descuento'] == 'porcentaje':
        descuento = (subtotal * float(cupon['valor_descuento'])) / 100
    else:
        descuento = float(cupon['valor_descuento'])
    
    # El descuento no puede ser mayor al subtotal
    descuento = min(descuento, subtotal)
    
    # Actualizar carrito
    costo_envio = float(carrito['costo_envio'])
    total = subtotal - descuento + costo_envio
    
    update_query = """
        UPDATE pedidos 
        SET cupon_aplicado = %s, descuento = %s, total = %s
        WHERE id = %s
    """
    execute_query(update_query, (cupon['codigo'], descuento, total, carrito['id']), fetch=False)
    
    print(f"Cupón aplicado - Descuento: ₡{descuento}")
    
    return {
        "success": True,
        "mensaje": "Cupón aplicado exitosamente",
        "cupon": {
            "codigo": cupon['codigo'],
            "descripcion": cupon['descripcion'],
            "descuento": descuento,
        },
        "carrito": {
            "subtotal": subtotal,
            "descuento": descuento,
            "total": total,
        }
    }

# ============= REMOVER CUPÓN DEL CARRITO =============
@router.delete("/remover/{usuario_id}")
def remover_cupon(usuario_id: int):
    """Remover cupón del carrito"""
    
    print(f" Removiendo cupón para usuario {usuario_id}")
    
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Buscar carrito
    carrito_query = """
        SELECT * FROM pedidos 
        WHERE cliente_id = %s AND estado = 'carrito'
    """
    carrito = execute_query(carrito_query, (cliente_id,))
    
    if not carrito:
        raise HTTPException(status_code=404, detail="No tienes un carrito activo")
    
    carrito = carrito[0]
    subtotal = float(carrito['subtotal'])
    costo_envio = float(carrito['costo_envio'])
    total = subtotal + costo_envio
    
    # Actualizar carrito
    update_query = """
        UPDATE pedidos 
        SET cupon_aplicado = NULL, descuento = 0, total = %s
        WHERE id = %s
    """
    execute_query(update_query, (total, carrito['id']), fetch=False)
    
    print(f"Cupón removido")
    
    return {
        "success": True,
        "mensaje": "Cupón removido",
        "carrito": {
            "subtotal": subtotal,
            "descuento": 0,
            "total": total,
        }
    }

# ============= CUPONES DISPONIBLES PARA USUARIO =============
@router.get("/disponibles/{usuario_id}")
def get_cupones_disponibles(usuario_id: int):
    """Obtener cupones disponibles para el usuario"""
    
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Obtener cupones activos
    cupones_query = """
        SELECT * FROM cupones 
        WHERE activo = TRUE 
        AND fecha_inicio <= CURDATE() 
        AND fecha_fin >= CURDATE()
        ORDER BY valor_descuento DESC
    """
    cupones = execute_query(cupones_query)
    
    cupones_disponibles = []
    
    for cupon in cupones:
        # Verificar usos del cliente
        usos_cliente_query = """
            SELECT COUNT(*) as total 
            FROM cupon_usos 
            WHERE cupon_id = %s AND cliente_id = %s
        """
        usos_cliente = execute_query(usos_cliente_query, (cupon['id'], cliente_id))
        usos_cliente_total = usos_cliente[0]['total']
        
        if usos_cliente_total >= cupon['usos_por_cliente']:
            continue
        
        # Verificar usos totales
        if cupon['usos_maximos']:
            usos_totales_query = """
                SELECT COUNT(*) as total 
                FROM cupon_usos 
                WHERE cupon_id = %s
            """
            usos_totales = execute_query(usos_totales_query, (cupon['id'],))
            if usos_totales[0]['total'] >= cupon['usos_maximos']:
                continue
        
        cupones_disponibles.append({
            "codigo": cupon['codigo'],
            "descripcion": cupon['descripcion'],
            "tipoDescuento": cupon['tipo_descuento'],
            "valorDescuento": float(cupon['valor_descuento']),
            "montoMinimo": float(cupon['monto_minimo']),
            "fechaFin": cupon['fecha_fin'].isoformat() if cupon['fecha_fin'] else None,
        })
    
    return cupones_disponibles

# ============= REGISTRAR USO DE CUPÓN =============
@router.post("/registrar-uso")
def registrar_uso_cupon(request: CuponUsoRequest):
    """Registrar el uso de un cupón"""
    
    # Buscar cupón
    cupon_query = "SELECT id FROM cupones WHERE codigo = %s"
    cupon = execute_query(cupon_query, (request.cuponCodigo,))
    
    if not cupon:
        return {"message": "Cupón no encontrado"}
    
    cupon_id = cupon[0]['id']
    
    # Buscar descuento del pedido
    pedido_query = "SELECT descuento FROM pedidos WHERE id = %s"
    pedido = execute_query(pedido_query, (request.pedidoId,))
    descuento = float(pedido[0]['descuento']) if pedido else 0
    
    # Registrar uso
    insert_query = """
        INSERT INTO cupon_usos (cupon_id, cliente_id, pedido_id, descuento_aplicado)
        VALUES (%s, %s, %s, %s)
    """
    execute_query(insert_query, (cupon_id, request.clienteId, request.pedidoId, descuento), fetch=False)
    
    print(f"Uso de cupón registrado")
    
    return {"message": "Uso de cupón registrado"}