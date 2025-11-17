
from fastapi import APIRouter, HTTPException, Query
from app.config.database import execute_query
from app.models.reportes import (ReporteVentasRequest)
from datetime import datetime, timedelta, date
from typing import Optional

router = APIRouter(
    prefix="/reportes",
    tags=["Reportes"]
)

# ============= REPORTE DE VENTAS =============
@router.get("/ventas")
def get_reporte_ventas(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
):
    """Obtener reporte de ventas en un rango de fechas"""
    
    # Fechas por defecto (últimos 30 días)
    if not fecha_inicio:
        inicio = date.today() - timedelta(days=30)
    else:
        inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    
    if not fecha_fin:
        fin = date.today()
    else:
        fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    
    print(f"Generando reporte de ventas: {inicio} a {fin}")
    
    # Pedidos completados en el rango
    query = """
        SELECT 
            p.id,
            p.total,
            p.fecha_completado
        FROM pedidos p
        WHERE p.estado = 'completado'
        AND DATE(p.fecha_completado) BETWEEN %s AND %s
    """
    pedidos = execute_query(query, (inicio, fin))
    
    total_ventas = sum(float(p['total']) for p in pedidos)
    total_pedidos = len(pedidos)
    ticket_promedio = total_ventas / total_pedidos if total_pedidos > 0 else 0
    
    # Productos más vendidos
    productos_query = """
        SELECT 
            pr.id,
            pr.nombre,
            SUM(pd.cantidad) as cantidad,
            SUM(pd.subtotal) as total
        FROM pedidos p
        JOIN pedido_detalles pd ON p.id = pd.pedido_id
        JOIN productos pr ON pd.producto_id = pr.id
        WHERE p.estado = 'completado'
        AND DATE(p.fecha_completado) BETWEEN %s AND %s
        GROUP BY pr.id, pr.nombre
        ORDER BY cantidad DESC
        LIMIT 5
    """
    top_productos = execute_query(productos_query, (inicio, fin))
    
    # Ventas por día
    ventas_dia_query = """
        SELECT 
            DATE(fecha_completado) as fecha,
            SUM(total) as total
        FROM pedidos
        WHERE estado = 'completado'
        AND DATE(fecha_completado) BETWEEN %s AND %s
        GROUP BY DATE(fecha_completado)
        ORDER BY fecha ASC
    """
    ventas_por_dia = execute_query(ventas_dia_query, (inicio, fin))
    
    print(f"Reporte generado: {total_pedidos} pedidos, ₡{total_ventas:,.0f}")
    
    return {
        "periodo": {
            "inicio": inicio.isoformat(),
            "fin": fin.isoformat()
        },
        "resumen": {
            "totalVentas": round(total_ventas, 2),
            "totalPedidos": total_pedidos,
            "ticketPromedio": round(ticket_promedio, 2)
        },
        "topProductos": [
            {
                "nombre": p['nombre'],
                "cantidad": int(p['cantidad']),
                "total": round(float(p['total']), 2)
            }
            for p in top_productos
        ],
        "ventasPorDia": [
            {
                "fecha": v['fecha'].isoformat() if hasattr(v['fecha'], 'isoformat') else str(v['fecha']),
                "total": round(float(v['total']), 2)
            }
            for v in ventas_por_dia
        ]
    }

# ============= MÉTRICAS GENERALES =============
@router.get("/metricas")
def get_metricas_generales():
    """Obtener métricas generales del sistema"""
    
    hoy = date.today()
    
    print(f"Obteniendo métricas generales para {hoy}")
    
    # Pedidos de hoy
    pedidos_hoy_query = """
        SELECT COUNT(*) as total
        FROM pedidos
        WHERE DATE(fecha_creacion) = %s AND estado = 'completado'
    """
    pedidos_hoy = execute_query(pedidos_hoy_query, (hoy,))
    
    # Ventas de hoy
    ventas_hoy_query = """
        SELECT COALESCE(SUM(total), 0) as total
        FROM pedidos
        WHERE DATE(fecha_creacion) = %s AND estado = 'completado'
    """
    ventas_hoy = execute_query(ventas_hoy_query, (hoy,))
    
    # Pedidos activos
    pedidos_activos_query = """
        SELECT COUNT(*) as total
        FROM pedidos
        WHERE estado IN ('confirmado', 'en_preparacion', 'listo', 'pendiente')
    """
    pedidos_activos = execute_query(pedidos_activos_query)
    
    # Productos
    productos_query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN disponible = TRUE THEN 1 ELSE 0 END) as disponibles
        FROM productos
    """
    productos = execute_query(productos_query)
    
    print(f"Métricas obtenidas")
    
    return {
        "hoy": {
            "pedidos": pedidos_hoy[0]['total'],
            "ventas": round(float(ventas_hoy[0]['total']), 2)
        },
        "pedidosActivos": pedidos_activos[0]['total'],
        "productos": {
            "total": productos[0]['total'],
            "disponibles": productos[0]['disponibles']
        }
    }

# ============= REPORTE DE PRODUCTOS =============
@router.get("/productos")
def get_reporte_productos():
    """Obtener reporte de productos"""
    
    print(f"Generando reporte de productos")
    
    # Productos por categoría
    categorias_query = """
        SELECT 
            c.nombre as categoria,
            COUNT(p.id) as total_productos,
            SUM(CASE WHEN p.disponible = TRUE THEN 1 ELSE 0 END) as disponibles
        FROM categorias c
        LEFT JOIN productos p ON c.id = p.categoria_id
        GROUP BY c.id, c.nombre
        ORDER BY total_productos DESC
    """
    por_categoria = execute_query(categorias_query)
    
    # Productos sin stock o agotados
    sin_stock_query = """
        SELECT 
            id,
            nombre,
            precio,
            disponible
        FROM productos
        WHERE disponible = FALSE
        ORDER BY nombre ASC
    """
    sin_stock = execute_query(sin_stock_query)
    
    print(f" Reporte de productos generado")
    
    return {
        "porCategoria": [
            {
                "categoria": c['categoria'],
                "totalProductos": c['total_productos'],
                "disponibles": c['disponibles']
            }
            for c in por_categoria
        ],
        "sinStock": [
            {
                "id": p['id'],
                "nombre": p['nombre'],
                "precio": float(p['precio'])
            }
            for p in sin_stock
        ]
    }

# ============= REPORTE DE CLIENTES =============
@router.get("/clientes")
def get_reporte_clientes():
    """Obtener reporte de clientes"""
    
    print(f" Generando reporte de clientes")
    
    # Total de clientes
    total_query = "SELECT COUNT(*) as total FROM clientes"
    total = execute_query(total_query)
    
    # Clientes con más pedidos
    top_clientes_query = """
        SELECT 
            c.id,
            c.nombre,
            c.email,
            COUNT(p.id) as total_pedidos,
            COALESCE(SUM(p.total), 0) as total_gastado
        FROM clientes c
        LEFT JOIN pedidos p ON c.id = p.cliente_id AND p.estado = 'completado'
        GROUP BY c.id, c.nombre, c.email
        HAVING total_pedidos > 0
        ORDER BY total_gastado DESC
        LIMIT 10
    """
    top_clientes = execute_query(top_clientes_query)
    
    # Clientes nuevos (últimos 30 días)
    nuevos_query = """
        SELECT COUNT(*) as total
        FROM clientes
        WHERE fecha_registro >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    """
    nuevos = execute_query(nuevos_query)
    
    print(f" Reporte de clientes generado")
    
    return {
        "totalClientes": total[0]['total'],
        "clientesNuevos30Dias": nuevos[0]['total'],
        "topClientes": [
            {
                "nombre": c['nombre'],
                "email": c['email'],
                "totalPedidos": c['total_pedidos'],
                "totalGastado": round(float(c['total_gastado']), 2)
            }
            for c in top_clientes
        ]
    }