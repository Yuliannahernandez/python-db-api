
import random
import time
from fastapi import APIRouter, HTTPException, Query,Request

from app.config.database import execute_query
from app.models.trivia import (
    IniciarPartidaRequest,  ResponderPreguntaRequest, FinalizarPartidaRequest
)   

router = APIRouter(
    prefix="/trivia",
    tags=["Trivia"]
)


@router.post("/iniciar")
def iniciar_partida(request: IniciarPartidaRequest):
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"  
    cliente = execute_query(cliente_query, (request.usuarioId,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Crear partida
    query = """
        INSERT INTO trivia_partidas 
        (cliente_id, pedido_id, puntaje_total, preguntas_correctas, preguntas_totales, completada)
        VALUES (%s, %s, 0, 0, 0, FALSE)
    """  
    result = execute_query(query, (cliente_id, request.pedidoId), fetch=False)
    
    return {
        "id": result['last_id'],
        "mensaje": "Partida iniciada exitosamente"
    }

# ============= OBTENER SIGUIENTE PREGUNTA =============
@router.get("/partida/{partida_id}/siguiente-pregunta")
def obtener_pregunta_siguiente(partida_id: int, usuarioId: int = Query(...)):
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"  
    cliente = execute_query(cliente_query, (usuarioId,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Verificar partida
    partida_query = """
        SELECT * FROM trivia_partidas 
        WHERE id = %s AND cliente_id = %s
    """  
    partida = execute_query(partida_query, (partida_id, cliente_id))
    
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    
    partida = partida[0]
    
    if partida['completada']:
        raise HTTPException(status_code=400, detail="La partida ya ha finalizado")
    
    # Obtener IDs de preguntas ya respondidas
    respondidas_query = """
        SELECT DISTINCT pregunta_id 
        FROM trivia_respuestas_jugador 
        WHERE partida_id = %s
    """ 
    respondidas = execute_query(respondidas_query, (partida_id,))
    ids_respondidas = [r['pregunta_id'] for r in respondidas]  
    
    # Buscar pregunta no respondida
    if ids_respondidas:
        placeholders = ','.join(['%s'] * len(ids_respondidas))
        pregunta_query = f"""
            SELECT * FROM trivia_preguntas 
            WHERE activa = TRUE AND id NOT IN ({placeholders})
            ORDER BY id ASC
            LIMIT 1
        """
        pregunta = execute_query(pregunta_query, tuple(ids_respondidas))
    else:
        pregunta_query = """
            SELECT * FROM trivia_preguntas 
            WHERE activa = TRUE
            ORDER BY id ASC
            LIMIT 1
        """
        pregunta = execute_query(pregunta_query)
    
    if not pregunta:
        raise HTTPException(status_code=404, detail="No hay más preguntas disponibles")
    
    pregunta = pregunta[0]
    
    # Obtener respuestas
    respuestas_query = """
        SELECT id, respuesta 
        FROM trivia_respuestas 
        WHERE pregunta_id = %s
        ORDER BY id ASC
    """ 
    respuestas = execute_query(respuestas_query, (pregunta['id'],))
    
    # Mezclar respuestas
    random.shuffle(respuestas)
    
    return {
        "pregunta": {
            "id": pregunta['id'],
            "pregunta": pregunta['pregunta'],
            "categoria": pregunta['categoria'],
            "dificultad": pregunta['dificultad']
        },
        "respuestas": [
            {"id": r['id'], "respuesta": r['respuesta']}
            for r in respuestas
        ]
    }

# ============= RESPONDER PREGUNTA =============
@router.post("/responder")
def responder_pregunta(request: ResponderPreguntaRequest):
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s" 
    cliente = execute_query(cliente_query, (request.usuarioId,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Verificar partida
    partida_query = """
        SELECT * FROM trivia_partidas 
        WHERE id = %s AND cliente_id = %s
    """  
    partida = execute_query(partida_query, (request.partidaId, cliente_id))
    
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    
    partida = partida[0]
    
    # Verificar respuesta
    respuesta_query = """
        SELECT * FROM trivia_respuestas 
        WHERE id = %s AND pregunta_id = %s
    """ 
    respuesta = execute_query(respuesta_query, (request.respuestaId, request.preguntaId))
    
    if not respuesta:
        raise HTTPException(status_code=404, detail="Respuesta no encontrada")
    
    respuesta = respuesta[0]
    es_correcta = bool(respuesta['es_correcta'])  
    
    # Calcular puntos
    puntos_ganados = 0
    if es_correcta:
        puntos_ganados = 100
        if request.tiempoRespuesta <= 5:
            puntos_ganados += 50
        elif request.tiempoRespuesta <= 10:
            puntos_ganados += 25
    
    # Guardar respuesta del jugador
    guardar_query = """
        INSERT INTO trivia_respuestas_jugador 
        (partida_id, pregunta_id, respuesta_seleccionada_id, es_correcta, tiempo_respuesta_segundos)
        VALUES (%s, %s, %s, %s, %s)
    """ 
    execute_query(guardar_query, (
        request.partidaId,
        request.preguntaId,
        request.respuestaId,
        es_correcta,
        request.tiempoRespuesta
    ), fetch=False)
    
    # Actualizar partida
    nuevas_preguntas_totales = partida['preguntas_totales'] + 1 
    nuevas_correctas = partida['preguntas_correctas'] + (1 if es_correcta else 0) 
    nuevo_puntaje = partida['puntaje_total'] + puntos_ganados  
    
    update_query = """
        UPDATE trivia_partidas 
        SET preguntas_totales = %s,
            preguntas_correctas = %s,
            puntaje_total = %s
        WHERE id = %s
    """ 
    execute_query(update_query, (
        nuevas_preguntas_totales,
        nuevas_correctas,
        nuevo_puntaje,
        request.partidaId
    ), fetch=False)
    
    return {
        "esCorrecta": es_correcta,
        "puntosGanados": puntos_ganados,
        "puntajeTotal": nuevo_puntaje,
        "correctas": nuevas_correctas
    }

# ============= FINALIZAR PARTIDA =============
@router.post("/finalizar")
def finalizar_partida(request: FinalizarPartidaRequest):
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"  
    cliente = execute_query(cliente_query, (request.usuarioId,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Buscar partida
    partida_query = """
        SELECT * FROM trivia_partidas 
        WHERE id = %s AND cliente_id = %s
    """
    partida = execute_query(partida_query, (request.partidaId, cliente_id))
    
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    
    partida = partida[0]
    
    # Calcular tiempo total
    tiempo_query = """
        SELECT SUM(tiempo_respuesta_segundos) as total 
        FROM trivia_respuestas_jugador 
        WHERE partida_id = %s
    """ 
    tiempo_result = execute_query(tiempo_query, (request.partidaId,))
    tiempo_total = int(tiempo_result[0]['total'] or 0)
    
    # Generar cupón si 4 o 5 correctas
    cupon_ganado = None
    cupon_id = None
    correctas = int(partida['preguntas_correctas']) 
    
    if correctas >= 4:
        cupon_ganado = generar_cupon_trivia(cliente_id, correctas)
        cupon_id = cupon_ganado['id']
    
    # Actualizar partida
    update_query = """
        UPDATE trivia_partidas 
        SET completada = TRUE,
            fecha_fin = NOW(),
            tiempo_total_segundos = %s,
            cupon_ganado_id = %s
        WHERE id = %s
    """ 
    execute_query(update_query, (tiempo_total, cupon_id, request.partidaId), fetch=False)
    
    return {
        "partidaId": partida['id'],
        "puntajeTotal": partida['puntaje_total'], 
        "correctas": correctas,
        "totales": partida['preguntas_totales'],  
        "tiempoTotal": tiempo_total,
        "cuponGanado": cupon_ganado
    }

def generar_cupon_trivia(cliente_id: int, correctas: int):
    """Genera cupón por trivia completada"""
    codigo = f"TRIVIA{cliente_id}{str(int(time.time()))[-6:]}"
    valor_descuento = 20 if correctas == 5 else 15
    
    from datetime import date, timedelta
    fecha_inicio = date.today()
    fecha_fin = fecha_inicio + timedelta(days=7)
    
    query = """
        INSERT INTO cupones 
        (codigo, descripcion, tipo_descuento, valor_descuento, monto_minimo,
         fecha_inicio, fecha_fin, usos_maximos, usos_por_cliente, activo)
        VALUES (%s, %s, 'porcentaje', %s, 5000, %s, %s, 1, 1, TRUE)
    """ 
    descripcion = f"Cupón ganado en Trivia - {correctas}/5 correctas"
    result = execute_query(query, (
        codigo, descripcion, valor_descuento, fecha_inicio, fecha_fin
    ), fetch=False)
    
    return {
        "id": result['last_id'],
        "codigo": codigo,
        "descripcion": descripcion,
        "tipoDescuento": "porcentaje",
        "valorDescuento": valor_descuento
    }

# ============= HISTORIAL DE PARTIDAS =============
@router.get("/historial/{usuario_id}")
def obtener_historial_trivia(usuario_id: int):
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"  
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        return []
    
    cliente_id = cliente[0]['id']
    
    # Obtener partidas completadas
    query = """
        SELECT 
            id,
            puntaje_total,
            preguntas_correctas,
            preguntas_totales,
            fecha_inicio,
            cupon_ganado_id
        FROM trivia_partidas
        WHERE cliente_id = %s AND completada = TRUE
        ORDER BY fecha_inicio DESC
        LIMIT 10
    """ 
    partidas = execute_query(query, (cliente_id,))
    
    return [
        {
            "id": p['id'],
            "puntajeTotal": p['puntaje_total'],  
            "correctas": p['preguntas_correctas'],  
            "totales": p['preguntas_totales'],  
            "fecha": p['fecha_inicio'].isoformat() if p['fecha_inicio'] else None,  
            "ganoCupon": p['cupon_ganado_id'] is not None 
        }
        for p in partidas
    ]

