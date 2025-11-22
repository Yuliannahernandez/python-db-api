from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.config.database import execute_query
from datetime import datetime
import random
import string

router = APIRouter(
    prefix="/sinpe",
    tags=["SINPE Móvil"]
)

class IniciarTransferenciaRequest(BaseModel):
    telefono_origen: str
    telefono_destino: str
    monto: float
    descripcion: str = None

class VerificarCodigoRequest(BaseModel):
    transaccion_id: int
    codigo: str


from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional

router = APIRouter(
    prefix="/sinpe",
    tags=["SINPE Móvil"]
)

@router.get("/mi-cuenta")
def get_mi_cuenta(usuario_id: Optional[str] = Header(None)):
    """Obtener cuenta bancaria del usuario actual"""
    
    if not usuario_id:
        raise HTTPException(status_code=401, detail="No autorizado")
    
    try:
        usuario_id_int = int(usuario_id)
    except:
        raise HTTPException(status_code=400, detail="usuario_id inválido")
    
    print(f" Obteniendo cuenta para usuario: {usuario_id_int}")
    
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id_int,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Buscar cuenta bancaria
    cuenta_query = """
        SELECT id, banco, numero_cuenta, numero_telefono, saldo, activa
        FROM cuentas_bancarias
        WHERE cliente_id = %s AND activa = TRUE
        LIMIT 1
    """
    cuenta = execute_query(cuenta_query, (cliente_id,))
    
    if not cuenta:
        # Crear cuenta automáticamente
        print(f" Cliente {cliente_id} no tiene cuenta, creando una...")
        
        import random
        telefono = '8' + ''.join([str(random.randint(0, 9)) for _ in range(7)])
        
        crear_cuenta_query = """
            INSERT INTO cuentas_bancarias (cliente_id, banco, numero_cuenta, numero_telefono, saldo)
            VALUES (%s, %s, %s, %s, %s)
        """
        execute_query(
            crear_cuenta_query,
            (cliente_id, 'BAC San José', f'CR{random.randint(10000000, 99999999)}', telefono, 500000.00),
            fetch=False
        )
        
        # Obtener la cuenta recién creada
        cuenta = execute_query(cuenta_query, (cliente_id,))
    
    cuenta_data = cuenta[0]
    
    return {
        "id": cuenta_data['id'],
        "banco": cuenta_data['banco'],
        "numeroCuenta": cuenta_data['numero_cuenta'],
        "telefono": cuenta_data['numero_telefono'],
        "saldo": float(cuenta_data['saldo']),
        "activa": bool(cuenta_data['activa'])
    }


@router.post("/iniciar-transferencia")
def iniciar_transferencia(request: IniciarTransferenciaRequest):
    """Iniciar una transferencia SINPE"""
    
    print(f"🇨🇷 Iniciando transferencia SINPE")
    print(f" Origen: {request.telefono_origen}")
    print(f" Destino: {request.telefono_destino}")
    print(f" Monto: ₡{request.monto:,.2f}")
    
    # 1. Buscar cuenta origen
    cuenta_origen_query = """
        SELECT id, saldo, banco
        FROM cuentas_bancarias
        WHERE numero_telefono = %s AND activa = TRUE
    """
    cuenta_origen = execute_query(cuenta_origen_query, (request.telefono_origen,))
    
    if not cuenta_origen:
        raise HTTPException(status_code=404, detail="Cuenta origen no encontrada")
    
    cuenta_origen_data = cuenta_origen[0]
    saldo_actual = float(cuenta_origen_data['saldo'])
    
    print(f"Cuenta origen: {cuenta_origen_data['banco']}, Saldo: ₡{saldo_actual:,.2f}")
    
    # 2. Validar saldo suficiente
    if saldo_actual < request.monto:
        print(f" Saldo insuficiente")
        raise HTTPException(
            status_code=400,
            detail=f"Saldo insuficiente. Disponible: ₡{saldo_actual:,.2f}"
        )
    
    # 3. Generar código de verificación de 6 dígitos
    import random
    import string
    codigo_verificacion = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    # 4. Generar número de comprobante único
    comprobante = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    
    # 5. Crear transacción pendiente
    transaccion_query = """
        INSERT INTO transacciones_sinpe 
        (cuenta_origen_id, telefono_destino, monto, comprobante, descripcion, estado, codigo_verificacion)
        VALUES (%s, %s, %s, %s, %s, 'pendiente', %s)
    """
    execute_query(
        transaccion_query,
        (cuenta_origen_data['id'], request.telefono_destino, request.monto, comprobante, request.descripcion, codigo_verificacion),
        fetch=False
    )
    
   
    transaccion_id_query = "SELECT id FROM transacciones_sinpe WHERE comprobante = %s"
    transaccion_result = execute_query(transaccion_id_query, (comprobante,))
    
    if not transaccion_result:
        raise HTTPException(status_code=500, detail="Error creando transacción")
    
    transaccion_id = transaccion_result[0]['id']
    
    print(f" Transacción creada: {transaccion_id}")
    print(f" Código de verificación: {codigo_verificacion}")
    print(f" Comprobante: {comprobante}")
    
    return {
        "transaccion_id": transaccion_id,
        "comprobante": comprobante,
        "codigo_verificacion": codigo_verificacion, 
        "monto": request.monto,
        "telefono_destino": request.telefono_destino,
        "mensaje": f"Código de verificación enviado al {request.telefono_origen}"
    }


@router.post("/verificar-codigo")
def verificar_codigo(request: VerificarCodigoRequest):
    """Verificar código y completar transferencia"""
    
    print(f"Verificando código para transacción {request.transaccion_id}")
    
    # 1. Buscar transacción
    transaccion_query = """
        SELECT 
            t.id,
            t.cuenta_origen_id,
            t.telefono_destino,
            t.monto,
            t.comprobante,
            t.estado,
            t.codigo_verificacion,
            c.saldo
        FROM transacciones_sinpe t
        JOIN cuentas_bancarias c ON t.cuenta_origen_id = c.id
        WHERE t.id = %s
    """
    transaccion = execute_query(transaccion_query, (request.transaccion_id,))
    
    if not transaccion:
        print(f"Transacción no encontrada con ID: {request.transaccion_id}")
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    
    trans_data = transaccion[0]
    
    print(f"Transacción encontrada:")
    print(f"   - Estado: {trans_data['estado']}")
    print(f"   - Código esperado: {trans_data['codigo_verificacion']}")
    print(f"   - Código recibido: {request.codigo}")
    
    # 2. Validar estado
    if trans_data['estado'] != 'pendiente':
        raise HTTPException(
            status_code=400,
            detail=f"Transacción ya {trans_data['estado']}"
        )
    
    # 3. Verificar código
    if trans_data['codigo_verificacion'] != request.codigo:
        print(f"Código incorrecto")
        raise HTTPException(status_code=400, detail="Código de verificación incorrecto")
    
    print(f"Código correcto")
    
    # 4. Validar saldo nuevamente (por si cambió)
    saldo_actual = float(trans_data['saldo'])
    monto = float(trans_data['monto'])
    
    if saldo_actual < monto:
        # Rechazar transacción
        update_query = "UPDATE transacciones_sinpe SET estado = 'rechazada' WHERE id = %s"
        execute_query(update_query, (request.transaccion_id,), fetch=False)
        raise HTTPException(status_code=400, detail="Saldo insuficiente")
    
    # 5. Descontar saldo de cuenta origen
    nuevo_saldo = saldo_actual - monto
    update_saldo_query = """
        UPDATE cuentas_bancarias 
        SET saldo = %s 
        WHERE id = %s
    """
    execute_query(update_saldo_query, (nuevo_saldo, trans_data['cuenta_origen_id']), fetch=False)
    
    print(f" Saldo descontado: ₡{monto:,.2f}")
    print(f" Nuevo saldo: ₡{nuevo_saldo:,.2f}")
    
    # 6. Acreditar a cuenta destino (si existe)
    cuenta_destino_query = """
        SELECT id, saldo 
        FROM cuentas_bancarias 
        WHERE numero_telefono = %s AND activa = TRUE
    """
    cuenta_destino = execute_query(cuenta_destino_query, (trans_data['telefono_destino'],))
    
    if cuenta_destino:
        saldo_destino = float(cuenta_destino[0]['saldo'])
        nuevo_saldo_destino = saldo_destino + monto
        execute_query(update_saldo_query, (nuevo_saldo_destino, cuenta_destino[0]['id']), fetch=False)
        print(f"Acreditado a destino: ₡{monto:,.2f}")
    
    # 7. Marcar transacción como completada
    update_transaccion_query = """
        UPDATE transacciones_sinpe 
        SET estado = 'completada', fecha_completado = NOW()
        WHERE id = %s
    """
    execute_query(update_transaccion_query, (request.transaccion_id,), fetch=False)
    
    print(f"Transferencia completada")
    
    return {
        "transaccion_id": request.transaccion_id,
        "comprobante": trans_data['comprobante'],
        "monto": monto,
        "estado": "completada",
        "mensaje": "Transferencia realizada exitosamente"
    }


@router.get("/transacciones")
def get_mis_transacciones():
    """Obtener historial de transacciones del usuario"""
    # TODO: 
    pass