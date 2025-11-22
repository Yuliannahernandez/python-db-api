from fastapi import APIRouter, HTTPException
from app.config.database import execute_query
import httpx
from datetime import datetime, date
import xml.etree.ElementTree as ET

router = APIRouter(
    prefix="/tipo-cambio",
    tags=["Tipo de Cambio"]
)

# Configuración BCCR
BCCR_API_URL = "https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/wsindicadoreseconomicos.asmx/ObtenerIndicadoresEconomicos"
INDICADOR_VENTA = "318"


TIPO_CAMBIO_DEFAULT = {
    "fecha": date.today().strftime("%d/%m/%Y"),
    "venta": 520.50,
    "compra": 510.00,
    "fuente": "default",
    "actualizado": datetime.now().isoformat()
}

@router.get("/actual")
async def get_tipo_cambio_actual():
    """Obtener el tipo de cambio actual del BCCR"""
    
    print("Intentando obtener tipo de cambio del BCCR...")
    
    try:
        fecha_hoy = date.today().strftime("%d/%m/%Y")
        
        params = {
            "Indicador": INDICADOR_VENTA,
            "FechaInicio": fecha_hoy,
            "FechaFinal": fecha_hoy,
            "Nombre": "TipoCambio",
            "SubNiveles": "N",
            "CorreoElectronico": "yulianahernandezc01@gmail.com",
            "Token": "RHE9CR0MDL"
        }
        
        print(f"Consultando BCCR con fecha: {fecha_hoy}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(BCCR_API_URL, params=params)
        
        print(f"Status BCCR: {response.status_code}")
        
        if response.status_code != 200:
            print(f" BCCR retornó status {response.status_code}")
            raise Exception("Error HTTP del BCCR")
        
        
        root = ET.fromstring(response.content)
        
        
        print(f"XML recibido (primeros 500 chars): {response.text[:500]}")
        
        
        tipo_cambio = None
        
        
        for item in root.findall(".//NUM_VALOR"):
            if item.text:
                tipo_cambio = float(item.text)
                break
        
       
        if not tipo_cambio:
            namespaces = {'ws': 'http://ws.sdde.bccr.fi.cr'}
            for item in root.findall(".//ws:NUM_VALOR", namespaces):
                if item.text:
                    tipo_cambio = float(item.text)
                    break
        
        if not tipo_cambio:
            print("No se encontró NUM_VALOR en el XML")
            print(f"Elementos encontrados: {[elem.tag for elem in root.iter()][:10]}")
            raise Exception("Valor no encontrado en XML")
        
        print(f"Tipo de cambio BCCR: ₡{tipo_cambio}")
        
        # Guardar en caché
        try:
            cache_query = """
                INSERT INTO tipo_cambio_cache (fecha, compra, venta, fecha_actualizacion)
                VALUES (%s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                venta = VALUES(venta),
                compra = VALUES(compra),
                fecha_actualizacion = NOW()
            """
            execute_query(cache_query, (fecha_hoy, tipo_cambio * 0.98, tipo_cambio), fetch=False)
            print("Guardado en caché")
        except Exception as cache_error:
            print(f"Error guardando caché: {cache_error}")
        
        return {
            "fecha": fecha_hoy,
            "venta": round(tipo_cambio, 2),
            "compra": round(tipo_cambio * 0.98, 2),
            "fuente": "BCCR",
            "actualizado": datetime.now().isoformat()
        }
        
    except httpx.TimeoutException:
        print("Timeout consultando BCCR, usando caché/default")
        return get_tipo_cambio_cache()
    except Exception as e:
        print(f"Error obteniendo del BCCR: {e}")
        print("Usando caché/default")
        return get_tipo_cambio_cache()


@router.get("/cache")
def get_tipo_cambio_cache():
    """Obtener tipo de cambio desde el caché local o default"""
    
    print("Buscando en caché...")
    
    try:
        query = """
            SELECT fecha, compra, venta, fecha_actualizacion
            FROM tipo_cambio_cache
            ORDER BY fecha DESC
            LIMIT 1
        """
        result = execute_query(query)
        
        if not result:
            print("No hay caché, usando default")
            return TIPO_CAMBIO_DEFAULT
        
        data = result[0]
        print(f"Usando caché: ₡{data['venta']}")
        
        return {
            "fecha": data['fecha'].strftime("%d/%m/%Y") if hasattr(data['fecha'], 'strftime') else str(data['fecha']),
            "venta": float(data['venta']),
            "compra": float(data['compra']),
            "fuente": "cache",
            "actualizado": data['fecha_actualizacion'].isoformat() if data['fecha_actualizacion'] else None
        }
        
    except Exception as e:
        print(f"Error en caché: {e}")
        print("Retornando default")
        return TIPO_CAMBIO_DEFAULT


@router.get("/convertir")
async def convertir_moneda(monto: float, de: str = "USD", a: str = "CRC"):
    """Convertir entre USD y CRC"""
    
    tipo_cambio_data = await get_tipo_cambio_actual()
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