from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
from dotenv import load_dotenv
import random  
import time
from app.routes import sucursales, usuarios,productos,categorias,profile,carrito,pedidos,trivia,lealtad,cupones,reportes,localidades,tipo_cambio,sinpe,recomendaciones,favoritos,reservaciones,tarjetas,tse
from app.routes.profile import router as profile_router 

# Cargar variables de entorno
load_dotenv()

app = FastAPI(
    title="Reelish Database API",
    description="API de Base de Datos para Restaurant App",
    version="1.0.0"
)

# ============= CORS =============
# Obtener orígenes permitidos desde variable de entorno
ALLOWED_ORIGINS = os.getenv(
    'ALLOWED_ORIGINS', 
    'http://localhost:3000,http://localhost:5173'
).split(',')

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Usar variable de entorno
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= CONFIGURACIÓN BD =============
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'restauranteapp.mysql.database.azure.com'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USERNAME', 'yulianahernandez'),
    'password': os.getenv('DB_PASSWORD', 'Sukipelusa2910#'),
    'database': os.getenv('DB_DATABASE', 'restaurant_app'),
    # NUEVO: Configuración SSL para Azure
    'ssl_disabled': False,
    'ssl_verify_cert': False,  # Para desarrollo, en producción usa True con certificado
    'autocommit': False,
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

def get_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"❌ Error de conexión a Azure MySQL: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error de conexión a base de datos: {str(e)}"
        )

def execute_query(query: str, params: tuple = None, fetch: bool = True):
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        if fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = {'affected_rows': cursor.rowcount, 'last_id': cursor.lastrowid}
        
        cursor.close()
        conn.close()
        return result
    except Error as e:
        print(f" Error en query: {e}")
        raise HTTPException(status_code=500, detail=f"Error en query: {str(e)}")





# ============= MODELOS PARA AUDITORÍA =============
class AuditoriaCreate(BaseModel):
    usuario_Id: int
    tabla: str
    accion: str  
    registro_Id: int = 0
    datos_Anteriores: Optional[str] = None
    datos_Nuevos: Optional[str] = None
    ip_Address: Optional[str] = None
    descripcion: Optional[str] = None
    endpoint: Optional[str] = None
    metodo: Optional[str] = None

# ============= AUDITORÍA =============
@app.post("/auditoria", status_code=status.HTTP_201_CREATED)
def create_auditoria(auditoria: AuditoriaCreate):
    query = """
        INSERT INTO auditoria 
        (usuario_Id, tabla, accion, registro_Id, datos_Anteriores, datos_Nuevos, 
         ip_Address, descripcion, endpoint, metodo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    result = execute_query(query, (
        auditoria.usuario_Id,
        auditoria.tabla,
        auditoria.accion,
        auditoria.registro_Id,
        auditoria.datos_Anteriores,
        auditoria.datos_Nuevos,
        auditoria.ip_Address,
        auditoria.descripcion,
        auditoria.endpoint,
        auditoria.metodo
    ), fetch=False)
    return {"id": result['last_id'], "message": "Auditoría creada"}

@app.get("/auditoria")
def get_auditorias(
    usuario_Id: Optional[int] = Query(None),
    tabla: Optional[str] = Query(None),
    accion: Optional[str] = Query(None),
    fechaDesde: Optional[str] = Query(None),
    fechaHasta: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0)
):
    conditions = []
    params = []
    
    if usuario_Id:
        conditions.append("a.usuario_Id = %s")
        params.append(usuario_Id)
    
    if tabla:
        conditions.append("a.tabla = %s")
        params.append(tabla)
    
    if accion:
        conditions.append("a.accion = %s")
        params.append(accion)
    
    if fechaDesde:
        conditions.append("a.fecha >= %s")
        params.append(fechaDesde)
    
    if fechaHasta:
        conditions.append("a.fecha <= %s")
        params.append(fechaHasta)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Contar total
    count_query = f"SELECT COUNT(*) as total FROM auditoria a WHERE {where_clause}"
    total_result = execute_query(count_query, tuple(params))
    total = total_result[0]['total']
    
    # Obtener registros
    params.extend([limit, offset])
    query = f"""
        SELECT 
            a.*,
            u.correo,
            c.nombre,
            c.apellido
        FROM auditoria a
        LEFT JOIN usuarios u ON a.usuario_Id = u.id
        LEFT JOIN clientes c ON u.id = c.usuario_Id
        WHERE {where_clause}
        ORDER BY a.fecha DESC
        LIMIT %s OFFSET %s
    """
    
    items = execute_query(query, tuple(params))
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/auditoria/{id}")
def get_auditoria_by_id(id: int):
    query = """
        SELECT 
            a.*,
            u.correo,
            c.nombre,
            c.apellido
        FROM auditoria a
        LEFT JOIN usuarios u ON a.usuario_Id = u.id
        LEFT JOIN clientes c ON u.id = c.usuario_Id
        WHERE a.id = %s
    """
    result = execute_query(query, (id,))
    if not result:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    return result[0]

@app.get("/auditoria/historial/{tabla}/{registro_id}")
def get_historial_registro(tabla: str, registro_id: int):
    query = """
        SELECT 
            a.*,
            u.correo,
            c.nombre,
            c.apellido
        FROM auditoria a
        LEFT JOIN usuarios u ON a.usuario_Id = u.id
        LEFT JOIN clientes c ON u.id = c.usuario_Id
        WHERE a.tabla = %s AND a.registro_Id = %s
        ORDER BY a.fecha DESC
    """
    return execute_query(query, (tabla, registro_id))

@app.get("/auditoria/estadisticas/general")
def get_estadisticas_auditoria(usuario_Id: Optional[int] = Query(None)):
    conditions = "WHERE usuario_Id = %s" if usuario_Id else ""
    params = (usuario_Id,) if usuario_Id else ()
    
    query = f"""
        SELECT 
            accion,
            COUNT(*) as total
        FROM auditoria
        {conditions}
        GROUP BY accion
    """
    
    resultados = execute_query(query, params)
    
    stats = {
        'totalInserts': 0,
        'totalUpdates': 0,
        'totalDeletes': 0,
        'totalSelects': 0,
        'total': 0
    }
    
    for row in resultados:
        accion = row['accion'].lower()
        total = int(row['total'])
        
        if accion == 'insert':
            stats['totalInserts'] = total
        elif accion == 'update':
            stats['totalUpdates'] = total
        elif accion == 'delete':
            stats['totalDeletes'] = total
        elif accion == 'select':
            stats['totalSelects'] = total
        
        stats['total'] += total
    
    return stats


# ============= INICIO =============
app.include_router(usuarios.router)
app.include_router(productos.router)
app.include_router(categorias.router)
app.include_router(profile.router)
app.include_router(sucursales.router)
app.include_router(carrito.router)
app.include_router(pedidos.router)
app.include_router(trivia.router)
app.include_router(lealtad.router)
app.include_router(cupones.router)
app.include_router(reportes.router)
app.include_router(localidades.router)
app.include_router(tipo_cambio.router)
app.include_router(sinpe.router)
app.include_router(recomendaciones.router)
app.include_router(favoritos.router)
app.include_router(reservaciones.router)
app.include_router(tarjetas.router)
app.include_router(tse.router)




@app.get("/")
def root():
    return {"message": "API funcionando correctamente"}

@app.get("/health")
def health_check():
    """Endpoint para verificar estado de la API y BD"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        
        return {
            "status": "healthy",
            "database": "connected ✅",
            "azure_mysql": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected ❌",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.getenv('PORT', 8000))
    print("Reelish Database API iniciada")
    print(f"Base de datos: {DB_CONFIG['database']}")
    print("Documentación: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", reload=True)