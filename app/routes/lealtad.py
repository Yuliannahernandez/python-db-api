
from fastapi import APIRouter, HTTPException
from app.config.database import execute_query
from app.models.lealtad import AgregarPuntosRequest, CanjearRecompensaRequest
from datetime import date, timedelta
import time

router = APIRouter(
    prefix="/lealtad",
    tags=["Lealtad"]
)

# ============= OBTENER PUNTOS DEL USUARIO =============
@router.get("/usuario/{usuario_id}")
def get_puntos_usuario(usuario_id: int):
    """Obtener puntos de lealtad del usuario"""
    
    # Buscar cliente
    cliente_query = "SELECT id, puntos_lealtad FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        return {"usuarioId": usuario_id, "puntos": 0}
    
    return {
        "usuarioId": usuario_id,
        "puntos": int(cliente[0]['puntos_lealtad'] or 0)
    }

# ============= AGREGAR PUNTOS POR COMPRA =============
@router.post("/agregar-puntos")
def agregar_puntos_por_compra(request: AgregarPuntosRequest):
    """Agregar puntos de lealtad por una compra"""
    
    print(f"Agregando puntos - Data recibida: {request}")
    
    usuario_id = request.usuarioId
    monto_compra = request.montoCompra
    pedido_id = request.pedidoId
    
    # Buscar cliente
    cliente_query = "SELECT id, puntos_lealtad FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        print(f"Cliente no encontrado para usuario_id={usuario_id}")
        return {"puntosGanados": 0, "error": "Cliente no encontrado"}
    
    cliente_id = cliente[0]['id']
    puntos_actuales = int(cliente[0]['puntos_lealtad'] or 0)
    
    # Calcular puntos (10 puntos por cada 1000 colones)
    puntos_ganados = int(monto_compra / 1000) * 10
    
    print(f" Monto: ₡{monto_compra} → {puntos_ganados} puntos")
    
    if puntos_ganados > 0:
        # Actualizar puntos del cliente
        nuevos_puntos = puntos_actuales + puntos_ganados
        update_query = "UPDATE clientes SET puntos_lealtad = %s WHERE id = %s"
        execute_query(update_query, (nuevos_puntos, cliente_id), fetch=False)
        
        print(f"Puntos actualizados: {puntos_actuales} → {nuevos_puntos}")
        
        # Registrar en historial (si existe la tabla)
        try:
            historial_query = """
                INSERT INTO puntos_historial 
                (cliente_id, puntos, tipo, pedido_id, descripcion)
                VALUES (%s, %s, 'ganado', %s, %s)
            """
            descripcion = f"Ganados por compra de ₡{int(monto_compra):,}"
            execute_query(historial_query, (cliente_id, puntos_ganados, pedido_id, descripcion), fetch=False)
        except Exception as e:
            print(f" No se pudo registrar en historial: {e}")
    
    return {
        "puntosGanados": puntos_ganados,
        "puntosTotal": puntos_actuales + puntos_ganados
    }

# ============= OBTENER HISTORIAL DE PUNTOS =============
@router.get("/historial/{usuario_id}")
def get_historial_puntos(usuario_id: int):
    """Obtener historial de puntos del usuario"""
    
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Obtener historial
    query = """
        SELECT 
            id,
            puntos,
            tipo,
            descripcion,
            fecha,
            pedido_id,
            recompensa_id
        FROM puntos_historial
        WHERE cliente_id = %s
        ORDER BY fecha DESC
        LIMIT 50
    """
    historial = execute_query(query, (cliente_id,))
    
    return [
        {
            "id": h['id'],
            "puntos": int(h['puntos']),
            "tipo": h['tipo'],
            "descripcion": h['descripcion'],
            "fecha": h['fecha'].isoformat() if h['fecha'] else None,
            "pedidoId": h['pedido_id'],
            "recompensaId": h['recompensa_id']
        }
        for h in historial
    ]

# ============= OBTENER RECOMPENSAS DISPONIBLES =============
@router.get("/recompensas")
def get_recompensas_disponibles():
    """Obtener todas las recompensas activas"""
    
    query = """
        SELECT 
            id,
            nombre,
            descripcion,
            puntos_requeridos,
            tipo,
            valor
        FROM recompensas
        WHERE activa = TRUE
        ORDER BY puntos_requeridos ASC
    """
    recompensas = execute_query(query)
    
    return [
        {
            "id": r['id'],
            "nombre": r['nombre'],
            "descripcion": r['descripcion'],
            "puntosRequeridos": int(r['puntos_requeridos']),
            "tipo": r['tipo'],
            "valor": r['valor']
        }
        for r in recompensas
    ]

# ============= CANJEAR RECOMPENSA =============
@router.post("/canjear")
def canjear_recompensa(request: CanjearRecompensaRequest):
    """Canjear una recompensa con puntos"""
    
    usuario_id = request.usuarioId
    recompensa_id = request.recompensaId
    
    # Buscar cliente
    cliente_query = "SELECT id, puntos_lealtad FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    puntos_actuales = int(cliente[0]['puntos_lealtad'])
    
    # Buscar recompensa
    recompensa_query = """
        SELECT * FROM recompensas 
        WHERE id = %s AND activa = TRUE
    """
    recompensa = execute_query(recompensa_query, (recompensa_id,))
    
    if not recompensa:
        raise HTTPException(status_code=404, detail="Recompensa no encontrada")
    
    recompensa = recompensa[0]
    puntos_requeridos = int(recompensa['puntos_requeridos'])
    
    # Validar puntos suficientes
    if puntos_actuales < puntos_requeridos:
        raise HTTPException(
            status_code=400,
            detail=f"No tienes suficientes puntos. Necesitas {puntos_requeridos} puntos y solo tienes {puntos_actuales}"
        )
    
    # Descontar puntos
    nuevos_puntos = puntos_actuales - puntos_requeridos
    update_query = "UPDATE clientes SET puntos_lealtad = %s WHERE id = %s"
    execute_query(update_query, (nuevos_puntos, cliente_id), fetch=False)
    
    # Registrar en historial
    historial_query = """
        INSERT INTO puntos_historial 
        (cliente_id, puntos, tipo, recompensa_id, descripcion)
        VALUES (%s, %s, 'canjeado', %s, %s)
    """
    descripcion = f"Canjeado: {recompensa['nombre']}"
    execute_query(historial_query, (cliente_id, -puntos_requeridos, recompensa_id, descripcion), fetch=False)
    
    # Generar cupón si es tipo cupón/descuento
    cupon_generado = None
    if recompensa['tipo'] in ['cupon', 'descuento']:
        cupon_generado = generar_cupon_recompensa(cliente_id, recompensa)
    
    return {
        "success": True,
        "mensaje": "Recompensa canjeada exitosamente",
        "puntosRestantes": nuevos_puntos,
        "recompensa": {
            "id": recompensa['id'],
            "nombre": recompensa['nombre'],
            "tipo": recompensa['tipo']
        },
        "cupon": cupon_generado
    }

def generar_cupon_recompensa(cliente_id: int, recompensa: dict):
    """Genera un cupón por canjear recompensa"""
    codigo = f"REWARD{cliente_id}{str(int(time.time()))[-6:]}"
    
    # Determinar tipo y valor de descuento
    tipo_descuento = 'monto_fijo'
    valor_descuento = 1000
    
    if recompensa['valor']:
        valor_str = str(recompensa['valor'])
        if '%' in valor_str:
            tipo_descuento = 'porcentaje'
            valor_descuento = float(valor_str.replace('%', ''))
        else:
            valor_descuento = float(valor_str)
    
    # Fechas (30 días de validez)
    fecha_inicio = date.today()
    fecha_fin = fecha_inicio + timedelta(days=30)
    
    # Crear cupón
    cupon_query = """
        INSERT INTO cupones 
        (codigo, descripcion, tipo_descuento, valor_descuento, monto_minimo, 
         fecha_inicio, fecha_fin, usos_maximos, usos_por_cliente, activo)
        VALUES (%s, %s, %s, %s, 0, %s, %s, 1, 1, TRUE)
    """
    descripcion = f"Recompensa canjeada: {recompensa['nombre']}"
    result = execute_query(cupon_query, (
        codigo, descripcion, tipo_descuento, valor_descuento,
        fecha_inicio, fecha_fin
    ), fetch=False)
    
    return {
        "id": result['last_id'],
        "codigo": codigo,
        "descripcion": descripcion,
        "tipoDescuento": tipo_descuento,
        "valorDescuento": valor_descuento,
        "fechaExpiracion": fecha_fin.isoformat()
    }