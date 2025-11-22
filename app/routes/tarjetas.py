
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import re
from datetime import datetime
from app.config.database import execute_query

router = APIRouter(
    prefix="/tarjetas",
    tags=["Tarjetas Simuladas"]
)

class ValidarTarjetaRequest(BaseModel):
    numero_tarjeta: str
    fecha_expiracion: str 
    cvv: str
    nombre_titular: str

class ProcesarPagoTarjetaRequest(BaseModel):
    numero_tarjeta: str
    fecha_expiracion: str
    cvv: str
    nombre_titular: str
    monto: float
    pedido_id: int

def detectar_tipo_tarjeta(numero: str) -> str:
    """Detectar el tipo de tarjeta según el número"""
    
    numero = numero.replace(' ', '')
    
    # Visa: Empieza con 4
    if numero.startswith('4'):
        return 'Visa'
    
    # Mastercard: Empieza con 51-55 o 2221-2720
    if numero[:2] in ['51', '52', '53', '54', '55']:
        return 'Mastercard'
    if 2221 <= int(numero[:4]) <= 2720:
        return 'Mastercard'
    
    # American Express: Empieza con 34 o 37
    if numero[:2] in ['34', '37']:
        return 'American Express'
    
    # Discover: Empieza con 6011, 622126-622925, 644-649, 65
    if numero.startswith('6011') or numero.startswith('65'):
        return 'Discover'
    if 622126 <= int(numero[:6]) <= 622925:
        return 'Discover'
    if 644 <= int(numero[:3]) <= 649:
        return 'Discover'
    
    return 'Desconocida'


def validar_numero_tarjeta(numero: str) -> bool:
    """Validar número de tarjeta usando algoritmo de Luhn (simplificado para pruebas)"""
    numero = numero.replace(' ', '')
    
    if not numero.isdigit():
        return False
    
    # Permitir longitudes comunes de tarjetas
    if len(numero) < 13 or len(numero) > 19:
        return False
    
    # aceptar tarjetas de prueba específicas
    tarjetas_prueba = [
        '4532015154231111',  # Visa - Saldo bajo
        '4532015154232222',  # Visa - Saldo medio
        '4532015154233333',  # Visa - Saldo alto
        '4532015154239999',  # Visa - Prueba
        '4532015154230000',  # Visa - Sin saldo
        '5425233430103333',  # Mastercard - Saldo alto
        '5425233430109999',  # Mastercard - Prueba
        '378282246314444',   # American Express
    ]
    
    if numero in tarjetas_prueba:
        return True
    
    # Algoritmo de Luhn para otras tarjetas
    def luhn_checksum(card_number):
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10
    
    return luhn_checksum(numero) == 0

def obtener_saldo_simulado(numero_tarjeta: str) -> float:
    """Simular saldo según los últimos 4 dígitos de la tarjeta"""
    ultimos_4 = numero_tarjeta[-4:]
    
    # Tarjetas de prueba con saldos específicos
    saldos_prueba = {
        '0000': 0.0,        # Sin saldo
        '1111': 5000.0,     # Saldo bajo
        '2222': 50000.0,    # Saldo medio
        '3333': 500000.0,   # Saldo alto
        '4444': 1000000.0,  # Saldo muy alto
        '9999': 999999.0,   # Tarjeta de prueba
    }
    
    if ultimos_4 in saldos_prueba:
        return saldos_prueba[ultimos_4]
    
    # Para otras tarjetas, generar saldo basado en los dígitos
    digitos_suma = sum(int(d) for d in ultimos_4)
    saldo = digitos_suma * 10000  # Entre 0 y 360,000 colones
    
    return float(saldo)

@router.post("/validar")
async def validar_tarjeta(request: ValidarTarjetaRequest):
    """Validar información de tarjeta (simulado)"""
    
    try:
        print(f"Validando tarjeta")
        
        numero = request.numero_tarjeta.replace(' ', '')
        
        # 1. Validar formato de número
        if not validar_numero_tarjeta(numero):
            return {
                "valida": False,
                "mensaje": "Número de tarjeta inválido",
                "tipo": None,
                "saldo": 0
            }
        
        # 2. Detectar tipo de tarjeta
        tipo_tarjeta = detectar_tipo_tarjeta(numero)
        
        # 3. Validar fecha de expiración
        try:
            mes, anio = request.fecha_expiracion.split('/')
            mes = int(mes)
            anio = int('20' + anio) if len(anio) == 2 else int(anio)
            
            fecha_expiracion = datetime(anio, mes, 1)
            fecha_actual = datetime.now()
            
            if fecha_expiracion < fecha_actual:
                return {
                    "valida": False,
                    "mensaje": "Tarjeta expirada",
                    "tipo": tipo_tarjeta,
                    "saldo": 0
                }
        except:
            return {
                "valida": False,
                "mensaje": "Fecha de expiración inválida",
                "tipo": tipo_tarjeta,
                "saldo": 0
            }
        
        # 4. Validar CVV
        if not request.cvv.isdigit() or len(request.cvv) not in [3, 4]:
            return {
                "valida": False,
                "mensaje": "CVV inválido",
                "tipo": tipo_tarjeta,
                "saldo": 0
            }
        
        # 5. Validar nombre del titular
        if len(request.nombre_titular.strip()) < 3:
            return {
                "valida": False,
                "mensaje": "Nombre del titular inválido",
                "tipo": tipo_tarjeta,
                "saldo": 0
            }
        
        # 6. Obtener saldo simulado
        saldo = obtener_saldo_simulado(numero)
        
        print(f"Tarjeta válida - Tipo: {tipo_tarjeta}, Saldo: ₡{saldo:,.2f}")
        
        return {
            "valida": True,
            "mensaje": "Tarjeta válida",
            "tipo": tipo_tarjeta,
            "saldo": saldo,
            "ultimos_digitos": numero[-4:]
        }
        
    except Exception as e:
        print(f"Error validando tarjeta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/procesar-pago")
async def procesar_pago_tarjeta(
    request: ProcesarPagoTarjetaRequest,
    usuario_id: int = Header(..., alias="usuario-id")
):
    """Procesar pago con tarjeta (simulado)"""
    
    try:
        print(f"Procesando pago - Monto: ₡{request.monto}")
        
        numero = request.numero_tarjeta.replace(' ', '')
        
        # 1. Validar tarjeta
        if not validar_numero_tarjeta(numero):
            raise HTTPException(status_code=400, detail="Número de tarjeta inválido")
        
        tipo_tarjeta = detectar_tipo_tarjeta(numero)
        saldo = obtener_saldo_simulado(numero)
        
        # 2. Validar fecha de expiración
        try:
            mes, anio = request.fecha_expiracion.split('/')
            mes = int(mes)
            anio = int('20' + anio) if len(anio) == 2 else int(anio)
            
            fecha_expiracion = datetime(anio, mes, 1)
            if fecha_expiracion < datetime.now():
                raise HTTPException(status_code=400, detail="Tarjeta expirada")
        except:
            raise HTTPException(status_code=400, detail="Fecha de expiración inválida")
        
        # 3. Validar CVV
        if not request.cvv.isdigit() or len(request.cvv) not in [3, 4]:
            raise HTTPException(status_code=400, detail="CVV inválido")
        
        # 4. Verificar saldo suficiente
        if saldo < request.monto:
            print(f"Saldo insuficiente - Saldo: ₡{saldo}, Monto: ₡{request.monto}")
            raise HTTPException(
                status_code=400,
                detail=f"Saldo insuficiente. Disponible: ₡{saldo:,.2f}"
            )
        
        # 5. Generar ID de transacción simulado
        import random
        import string
        transaction_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
        
        # 6. Actualizar pedido en la base de datos
        update_query = """
            UPDATE pedidos 
            SET estado = 'confirmado',
                metodo_pago = 'tarjeta',
                tarjeta_tipo = %s,
                tarjeta_ultimos_digitos = %s,
                transaction_id = %s,
                fecha_confirmacion = NOW()
            WHERE id = %s
        """
        execute_query(
            update_query,
            (tipo_tarjeta, numero[-4:], transaction_id, request.pedido_id),
            fetch=False
        )
        
        
        insert_transaccion = """
            INSERT INTO transacciones (
                pedido_id, tipo_pago, monto, 
                tarjeta_tipo, tarjeta_ultimos_digitos,
                transaction_id, estado, fecha_transaccion
            )
            VALUES (%s, 'tarjeta', %s, %s, %s, %s, 'aprobado', NOW())
        """
        execute_query(
            insert_transaccion,
            (request.pedido_id, request.monto, tipo_tarjeta, numero[-4:], transaction_id),
            fetch=False
        )
        
        print(f"Pago procesado exitosamente - Transaction ID: {transaction_id}")
        
        return {
            "success": True,
            "message": "Pago procesado exitosamente",
            "transaction_id": transaction_id,
            "tipo_tarjeta": tipo_tarjeta,
            "ultimos_digitos": numero[-4:],
            "monto": request.monto,
            "pedido_id": request.pedido_id,
            "fecha_transaccion": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error procesando pago: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tarjetas-prueba")
async def obtener_tarjetas_prueba():
    """Obtener lista de tarjetas de prueba para desarrollo"""
    
    return {
        "tarjetas_prueba": [
            {
                "tipo": "Visa",
                "numero": "4532 0151 5423 1111",
                "cvv": "123",
                "expiracion": "12/25",
                "nombre": "Yuliana Hernández",
                "saldo": 5000.0,
                "descripcion": "Saldo bajo"
            },
            {
                "tipo": "Visa",
                "numero": "4532 0151 5423 2222",
                "cvv": "456",
                "expiracion": "12/26",
                "nombre": "María González",
                "saldo": 50000.0,
                "descripcion": "Saldo medio"
            },
            {
                "tipo": "Mastercard",
                "numero": "5425 2334 3010 3333",
                "cvv": "789",
                "expiracion": "01/27",
                "nombre": "Carlos Rodríguez",
                "saldo": 500000.0,
                "descripcion": "Saldo alto"
            },
            {
                "tipo": "Mastercard",
                "numero": "5425 2334 3010 9999",
                "cvv": "321",
                "expiracion": "06/28",
                "nombre": "Ana Martínez",
                "saldo": 999999.0,
                "descripcion": "Tarjeta de prueba"
            },
            {
                "tipo": "American Express",
                "numero": "3782 822463 14444",
                "cvv": "1234",
                "expiracion": "03/27",
                "nombre": "Luis Fernández",
                "saldo": 1000000.0,
                "descripcion": "Saldo muy alto"
            },
            {
                "tipo": "Visa",
                "numero": "4532 0151 5423 0000",
                "cvv": "111",
                "expiracion": "12/25",
                "nombre": "Pedro López",
                "saldo": 0.0,
                "descripcion": "Sin saldo (para probar rechazo)"
            }
        ],
        "nota": "Estas son tarjetas simuladas para pruebas. El saldo se determina por los últimos 4 dígitos."
    }