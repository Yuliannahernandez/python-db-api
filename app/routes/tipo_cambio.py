# routes/tipo_cambio.py

from fastapi import APIRouter, HTTPException
from app.config.database import execute_query
import httpx  # ← Cambiar requests por httpx
from datetime import datetime, date
import xml.etree.ElementTree as ET

router = APIRouter(
    prefix="/tipo-cambio",
    tags=["Tipo de Cambio"]
)

# Configuración BCCR
BCCR_API_URL = "https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/wsindicadoreseconomicos.asmx/ObtenerIndicadoresEconomicos"

# Indicadores BCCR
INDICADOR_VENTA = "318"  # Tipo de cambio venta
INDICADOR_COMPRA = "317"  # Tipo de cambio compra

@router.get("/actual")
async def get_tipo_cambio_actual():  # ← Agregar async
    """Obtener el tipo de cambio actual del BCCR"""
    
    print(f"💱 Obteniendo tipo de cambio del BCCR")
    
    try:
        # Fecha actual
        fecha_hoy = date.today().strftime("%d/%m/%Y")
        
        # Parámetros para la API del BCCR
        params = {
            "Indicador": INDICADOR_VENTA,
            "FechaInicio": fecha_hoy,
            "FechaFinal": fecha_hoy,
            "Nombre": "TipoCambio",
            "SubNiveles": "N",
            "CorreoElectronico": "yulianahernandezc01@gmail.com",
            "Token": "RHE9CR0MDL"
        }
        
        # Hacer petición al BCCR usando httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(BCCR_API_URL, params=params)
        
        if response.status_code != 200:
            print(f"⚠️ Error BCCR status: {response.status_code}")
            raise Exception("Error al consultar BCCR")
        
        # Parsear XML
        root = ET.fromstring(response.content)
        
        # Extraer valor del tipo de cambio
        tipo_cambio = None
        for item in root.findall(".//{http://ws.sdde.bccr.fi.cr}NUM_VALOR"):
            tipo_cambio = float(item.text)
            break
        
        if not tipo_cambio:
            print("⚠️ No se encontró valor en XML")
            raise Exception("No se encontró el tipo de cambio")
        
        print(f"✅ Tipo de cambio obtenido del BCCR: ₡{tipo_cambio}")
        
        # Guardar en caché en la base de datos
        try:
            cache_query = """
                INSERT INTO tipo_cambio_cache (fecha, compra, venta, fecha_actualizacion)
                VALUES (%s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                venta = VALUES(venta),
                fecha_actualizacion = NOW()
            """
            execute_query(cache_query, (fecha_hoy, tipo_cambio, tipo_cambio), fetch=False)
        except Exception as cache_error:
            print(f"⚠️ Error guardando en caché: {cache_error}")
        
        return {
            "fecha": fecha_hoy,
            "venta": round(tipo_cambio, 2),
            "compra": round(tipo_cambio, 2),
            "fuente": "BCCR",
            "actualizado": datetime.now().isoformat()
        }
        
    except httpx.TimeoutException:  # ← Cambiar excepción
        print("⚠️ Timeout al consultar BCCR, usando caché")
        return get_tipo_cambio_cache()
    except Exception as e:
        print(f"❌ Error obteniendo tipo de cambio: {e}")
        return get_tipo_cambio_cache()

@router.get("/cache")
def get_tipo_cambio_cache():
    """Obtener tipo de cambio desde el caché local"""
    
    print(f"💾 Obteniendo tipo de cambio desde caché")
    
    try:
        query = """
            SELECT fecha, compra, venta, fecha_actualizacion
            FROM tipo_cambio_cache
            ORDER BY fecha DESC
            LIMIT 1
        """
        result = execute_query(query)
        
        if not result:
            # Valor por defecto si no hay caché
            print("⚠️ No hay caché, usando valor por defecto")
            return {
                "fecha": date.today().strftime("%d/%m/%Y"),
                "venta": 520.00,
                "compra": 520.00,
                "fuente": "default",
                "actualizado": None
            }
        
        data = result[0]
        print(f"✅ Tipo de cambio desde caché: ₡{data['venta']}")
        
        return {
            "fecha": data['fecha'].strftime("%d/%m/%Y") if hasattr(data['fecha'], 'strftime') else str(data['fecha']),
            "venta": float(data['venta']),
            "compra": float(data['compra']),
            "fuente": "cache",
            "actualizado": data['fecha_actualizacion'].isoformat() if data['fecha_actualizacion'] else None
        }
        
    except Exception as e:
        print(f"❌ Error obteniendo caché: {e}")
        # Retornar valor por defecto en lugar de lanzar error
        return {
            "fecha": date.today().strftime("%d/%m/%Y"),
            "venta": 520.00,
            "compra": 520.00,
            "fuente": "error-default",
            "actualizado": None
        }

@router.get("/convertir")
async def convertir_moneda(monto: float, de: str = "USD", a: str = "CRC"):  # ← Agregar async
    """Convertir entre USD y CRC"""
    
    tipo_cambio_data = await get_tipo_cambio_actual()  # ← Agregar await
    tipo_cambio = tipo_cambio_data['venta']
    
    if de == "USD" and a == "CRC":
        resultado = monto * tipo_cambio
    elif de == "CRC" and a == "USD":
        resultado = monto / tipo_cambio
    else:
        raise HTTPException(status_code=400, detail="Monedas no soportadas")
    
    return {
        "monto_original": monto,
        "moneda_original": de,
        "monto_convertido": round(resultado, 2),
        "moneda_destino": a,
        "tipo_cambio": tipo_cambio,
        "fecha": tipo_cambio_data['fecha']
    }