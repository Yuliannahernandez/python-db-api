
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, time, timedelta
from app.config.database import execute_query

router = APIRouter(
    prefix="/reservaciones",
    tags=["Reservaciones"]
)

class CrearReservacionRequest(BaseModel):
    sucursal_id: int
    fecha_reservacion: str 
    hora_reservacion: str  
    numero_personas: int
    notas_especiales: Optional[str] = None
    telefono_contacto: str

class ModificarReservacionRequest(BaseModel):
    fecha_reservacion: Optional[str] = None
    hora_reservacion: Optional[str] = None
    numero_personas: Optional[int] = None
    notas_especiales: Optional[str] = None

@router.get("/disponibilidad")
async def verificar_disponibilidad(
    sucursal_id: int,
    fecha: str,
):
    """Obtener horarios disponibles para una fecha específica"""
    
    try:
        print(f"Verificando disponibilidad - Sucursal: {sucursal_id}, Fecha: {fecha}")
        
        # Validar fecha
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
        
        if fecha_obj < date.today():
            raise HTTPException(status_code=400, detail="No se pueden hacer reservaciones en fechas pasadas")
        
        # Obtener día de la semana
        dias_semana = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        dia_semana = dias_semana[fecha_obj.weekday()]
        
        # Obtener horarios configurados
        horarios_query = """
            SELECT id, hora_inicio, hora_fin, capacidad_maxima
            FROM horarios_disponibles
            WHERE sucursal_id = %s AND dia_semana = %s AND activo = TRUE
            ORDER BY hora_inicio
        """
        horarios = execute_query(horarios_query, (sucursal_id, dia_semana))
        
        if not horarios:
            return {
                "fecha": fecha,
                "dia_semana": dia_semana,
                "horarios_disponibles": [],
                "mensaje": "No hay horarios disponibles para este día"
            }
        
        # Para cada horario, verificar reservaciones
        horarios_disponibles = []
        for horario in horarios:
            # Convertir hora_inicio (puede ser timedelta o time) a string
            hora_inicio = horario['hora_inicio']
            
            
            if isinstance(hora_inicio, timedelta):
                total_seconds = int(hora_inicio.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                hora_str = f"{hours:02d}:{minutes:02d}"
            elif isinstance(hora_inicio, time):
                hora_str = hora_inicio.strftime('%H:%M')
            else:
                # Si es string, usar directamente
                hora_str = str(hora_inicio)
            
            # Contar reservaciones existentes
            reservaciones_query = """
                SELECT COUNT(*) as total, COALESCE(SUM(numero_personas), 0) as personas_reservadas
                FROM reservaciones
                WHERE sucursal_id = %s 
                AND fecha_reservacion = %s
                AND hora_reservacion = %s
                AND estado IN ('pendiente', 'confirmada')
            """
            reservaciones = execute_query(
                reservaciones_query, 
                (sucursal_id, fecha, hora_str)
            )
            
            personas_reservadas = int(reservaciones[0]['personas_reservadas'])
            capacidad_disponible = horario['capacidad_maxima'] - personas_reservadas
            
            horarios_disponibles.append({
                "hora": hora_str,
                "capacidad_maxima": horario['capacidad_maxima'],
                "capacidad_disponible": capacidad_disponible,
                "disponible": capacidad_disponible > 0
            })
        
        return {
            "fecha": fecha,
            "dia_semana": dia_semana,
            "horarios_disponibles": horarios_disponibles
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verificando disponibilidad: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/crear")
async def crear_reservacion(
    request: CrearReservacionRequest,
    usuario_id: int = Header(..., alias="usuario-id")
):
    """Crear una nueva reservación"""
    
    try:
        print(f"Creando reservación - Usuario: {usuario_id}")
        
        cliente_query = "SELECT id, nombre FROM clientes WHERE usuario_id = %s"
        cliente = execute_query(cliente_query, (usuario_id,))
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        cliente_id = cliente[0]['id']
        
        try:
            fecha_obj = datetime.strptime(request.fecha_reservacion, '%Y-%m-%d').date()
            hora_obj = datetime.strptime(request.hora_reservacion, '%H:%M').time()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha u hora inválido")
        
        if fecha_obj < date.today():
            raise HTTPException(status_code=400, detail="No se pueden hacer reservaciones en fechas pasadas")
        
        dias_semana = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        dia_semana = dias_semana[fecha_obj.weekday()]
        
        # Verificar horario disponible usando string de hora
        horario_query = """
            SELECT id, capacidad_maxima, hora_inicio
            FROM horarios_disponibles
            WHERE sucursal_id = %s 
            AND dia_semana = %s 
            AND activo = TRUE
        """
        horarios = execute_query(horario_query, (request.sucursal_id, dia_semana))
        
        if not horarios:
            raise HTTPException(status_code=400, detail="No hay horarios disponibles para este día")
        
        # Buscar el horario que coincida
        horario_encontrado = None
        for h in horarios:
            hora_inicio = h['hora_inicio']
            
            # Convertir a string
            if isinstance(hora_inicio, timedelta):
                total_seconds = int(hora_inicio.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                hora_str = f"{hours:02d}:{minutes:02d}"
            elif isinstance(hora_inicio, time):
                hora_str = hora_inicio.strftime('%H:%M')
            else:
                hora_str = str(hora_inicio)
            
            if hora_str == request.hora_reservacion:
                horario_encontrado = h
                break
        
        if not horario_encontrado:
            raise HTTPException(status_code=400, detail="Horario no disponible")
        
        # Verificar capacidad
        capacidad_query = """
            SELECT COALESCE(SUM(numero_personas), 0) as personas_reservadas
            FROM reservaciones
            WHERE sucursal_id = %s 
            AND fecha_reservacion = %s
            AND hora_reservacion = %s
            AND estado IN ('pendiente', 'confirmada')
        """
        capacidad_result = execute_query(
            capacidad_query,
            (request.sucursal_id, request.fecha_reservacion, request.hora_reservacion)
        )
        
        personas_reservadas = int(capacidad_result[0]['personas_reservadas'])
        capacidad_disponible = horario_encontrado['capacidad_maxima'] - personas_reservadas
        
        if request.numero_personas > capacidad_disponible:
            raise HTTPException(
                status_code=400, 
                detail=f"No hay capacidad suficiente. Disponible: {capacidad_disponible} personas"
            )
        
        # Crear reservación
        insert_query = """
            INSERT INTO reservaciones (
                cliente_id, sucursal_id, fecha_reservacion, hora_reservacion,
                numero_personas, notas_especiales, telefono_contacto, estado
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pendiente')
        """
        execute_query(
            insert_query,
            (
                cliente_id,
                request.sucursal_id,
                request.fecha_reservacion,
                request.hora_reservacion,
                request.numero_personas,
                request.notas_especiales,
                request.telefono_contacto
            ),
            fetch=False
        )
        
        # Obtener la reservación creada
        reservacion_query = """
            SELECT r.*, s.nombre as sucursal_nombre, c.nombre as cliente_nombre
            FROM reservaciones r
            JOIN sucursales s ON r.sucursal_id = s.id
            JOIN clientes c ON r.cliente_id = c.id
            WHERE r.cliente_id = %s
            AND r.fecha_reservacion = %s
            AND r.hora_reservacion = %s
            ORDER BY r.fecha_creacion DESC
            LIMIT 1
        """
        reservacion = execute_query(
            reservacion_query,
            (cliente_id, request.fecha_reservacion, request.hora_reservacion)
        )
        
        if reservacion:
            res = reservacion[0]
            print(f" Reservación creada - ID: {res['id']}")
            
            # Convertir hora_reservacion a string
            hora_reservacion = res['hora_reservacion']
            if isinstance(hora_reservacion, timedelta):
                total_seconds = int(hora_reservacion.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                hora_str = f"{hours:02d}:{minutes:02d}"
            elif isinstance(hora_reservacion, time):
                hora_str = hora_reservacion.strftime('%H:%M')
            else:
                hora_str = str(hora_reservacion)
            
            return {
                "message": "Reservación creada exitosamente",
                "reservacion": {
                    "id": res['id'],
                    "sucursalNombre": res['sucursal_nombre'],
                    "fechaReservacion": res['fecha_reservacion'].isoformat() if hasattr(res['fecha_reservacion'], 'isoformat') else str(res['fecha_reservacion']),
                    "horaReservacion": hora_str,
                    "numeroPersonas": res['numero_personas'],
                    "estado": res['estado'],
                    "notasEspeciales": res['notas_especiales'],
                    "telefonoContacto": res['telefono_contacto']
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Error al crear la reservación")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f" Error creando reservación: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mis-reservaciones")
async def obtener_mis_reservaciones(
    usuario_id: int = Header(..., alias="usuario-id")
):
    """Obtener todas las reservaciones del usuario"""
    
    try:
        print(f"Obteniendo reservaciones para usuario: {usuario_id}")
        
        cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
        cliente = execute_query(cliente_query, (usuario_id,))
        
        if not cliente:
            return {"reservaciones": [], "total": 0}
        
        cliente_id = cliente[0]['id']
        
        reservaciones_query = """
            SELECT 
                r.*,
                s.nombre as sucursal_nombre,
                s.direccion as sucursal_direccion,
                s.telefono as sucursal_telefono
            FROM reservaciones r
            JOIN sucursales s ON r.sucursal_id = s.id
            WHERE r.cliente_id = %s
            ORDER BY r.fecha_reservacion DESC, r.hora_reservacion DESC
        """
        reservaciones = execute_query(reservaciones_query, (cliente_id,))
        
        resultado = []
        for res in reservaciones:
            # Convertir fecha_reservacion
            if hasattr(res['fecha_reservacion'], 'isoformat'):
                fecha_str = res['fecha_reservacion'].isoformat()
            else:
                fecha_str = str(res['fecha_reservacion'])
            
            
            hora_reservacion = res['hora_reservacion']
            if isinstance(hora_reservacion, timedelta):
                total_seconds = int(hora_reservacion.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                hora_str = f"{hours:02d}:{minutes:02d}"
            elif isinstance(hora_reservacion, time):
                hora_str = hora_reservacion.strftime('%H:%M')
            else:
                hora_str = str(hora_reservacion)
            
            # Convertir fecha_creacion
            if hasattr(res['fecha_creacion'], 'isoformat'):
                fecha_creacion_str = res['fecha_creacion'].isoformat()
            else:
                fecha_creacion_str = str(res['fecha_creacion'])
            
            resultado.append({
                "id": res['id'],
                "sucursal": {
                    "id": res['sucursal_id'],
                    "nombre": res['sucursal_nombre'],
                    "direccion": res['sucursal_direccion'],
                    "telefono": res['sucursal_telefono']
                },
                "fechaReservacion": fecha_str,
                "horaReservacion": hora_str,
                "numeroPersonas": res['numero_personas'],
                "mesaAsignada": res['mesa_asignada'],
                "estado": res['estado'],
                "notasEspeciales": res['notas_especiales'],
                "telefonoContacto": res['telefono_contacto'],
                "fechaCreacion": fecha_creacion_str
            })
        
        print(f"{len(resultado)} reservaciones encontradas")
        
        return {
            "reservaciones": resultado,
            "total": len(resultado)
        }
        
    except Exception as e:
        print(f" Error obteniendo reservaciones: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{reservacion_id}")
async def obtener_detalle_reservacion(
    reservacion_id: int,
    usuario_id: int = Header(..., alias="usuario-id")
):
    """Obtener detalle de una reservación específica"""
    
    try:
        # Buscar cliente
        cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
        cliente = execute_query(cliente_query, (usuario_id,))
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        cliente_id = cliente[0]['id']
        
        # Obtener reservación
        reservacion_query = """
            SELECT 
                r.*,
                s.nombre as sucursal_nombre,
                s.direccion as sucursal_direccion,
                s.telefono as sucursal_telefono,
                s.provincia as sucursal_provincia
            FROM reservaciones r
            JOIN sucursales s ON r.sucursal_id = s.id
            WHERE r.id = %s AND r.cliente_id = %s
        """
        reservacion = execute_query(reservacion_query, (reservacion_id, cliente_id))
        
        if not reservacion:
            raise HTTPException(status_code=404, detail="Reservación no encontrada")
        
        res = reservacion[0]
        
        return {
            "id": res['id'],
            "sucursal": {
                "id": res['sucursal_id'],
                "nombre": res['sucursal_nombre'],
                "direccion": res['sucursal_direccion'],
                "telefono": res['sucursal_telefono'],
                "provincia": res['sucursal_provincia']
            },
            "fechaReservacion": res['fecha_reservacion'].isoformat(),
            "horaReservacion": res['hora_reservacion'].strftime('%H:%M'),
            "numeroPersonas": res['numero_personas'],
            "mesaAsignada": res['mesa_asignada'],
            "estado": res['estado'],
            "notasEspeciales": res['notas_especiales'],
            "telefonoContacto": res['telefono_contacto'],
            "fechaCreacion": res['fecha_creacion'].isoformat(),
            "fechaModificacion": res['fecha_modificacion'].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error obteniendo detalle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{reservacion_id}/modificar")
async def modificar_reservacion(
    reservacion_id: int,
    request: ModificarReservacionRequest,
    usuario_id: int = Header(..., alias="usuario-id")
):
    """Modificar una reservación existente"""
    
    try:
        print(f" Modificando reservación {reservacion_id}")
        
        # Buscar cliente
        cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
        cliente = execute_query(cliente_query, (usuario_id,))
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        cliente_id = cliente[0]['id']
        
        # Verificar que la reservación existe y pertenece al cliente
        reservacion_query = """
            SELECT * FROM reservaciones 
            WHERE id = %s AND cliente_id = %s
        """
        reservacion = execute_query(reservacion_query, (reservacion_id, cliente_id))
        
        if not reservacion:
            raise HTTPException(status_code=404, detail="Reservación no encontrada")
        
        res = reservacion[0]
        
        # No permitir modificar reservaciones canceladas o completadas
        if res['estado'] in ['cancelada', 'completada', 'no_asistio']:
            raise HTTPException(
                status_code=400,
                detail=f"No se puede modificar una reservación con estado '{res['estado']}'"
            )
        
        
        updates = []
        params = []
        
        if request.fecha_reservacion:
            fecha_obj = datetime.strptime(request.fecha_reservacion, '%Y-%m-%d').date()
            if fecha_obj < date.today():
                raise HTTPException(status_code=400, detail="No se puede reservar en fechas pasadas")
            updates.append("fecha_reservacion = %s")
            params.append(request.fecha_reservacion)
        
        if request.hora_reservacion:
            updates.append("hora_reservacion = %s")
            params.append(request.hora_reservacion)
        
        if request.numero_personas:
            updates.append("numero_personas = %s")
            params.append(request.numero_personas)
        
        if request.notas_especiales is not None:
            updates.append("notas_especiales = %s")
            params.append(request.notas_especiales)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No hay cambios para actualizar")
        
        # Actualizar
        params.append(reservacion_id)
        update_query = f"""
            UPDATE reservaciones 
            SET {', '.join(updates)}
            WHERE id = %s
        """
        execute_query(update_query, tuple(params), fetch=False)
        
        print(f" Reservación modificada exitosamente")
        
        return {
            "message": "Reservación modificada exitosamente",
            "reservacion_id": reservacion_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error modificando reservación: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{reservacion_id}/cancelar")
async def cancelar_reservacion(
    reservacion_id: int,
    usuario_id: int = Header(..., alias="usuario-id")
):
    """Cancelar una reservación"""
    
    try:
        print(f"Cancelando reservación {reservacion_id}")
        
        # Buscar cliente
        cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
        cliente = execute_query(cliente_query, (usuario_id,))
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        cliente_id = cliente[0]['id']
        
        # Verificar que la reservación existe
        reservacion_query = """
            SELECT * FROM reservaciones 
            WHERE id = %s AND cliente_id = %s
        """
        reservacion = execute_query(reservacion_query, (reservacion_id, cliente_id))
        
        if not reservacion:
            raise HTTPException(status_code=404, detail="Reservación no encontrada")
        
        res = reservacion[0]
        
        # No permitir cancelar si ya está cancelada o completada
        if res['estado'] in ['cancelada', 'completada']:
            raise HTTPException(
                status_code=400,
                detail=f"No se puede cancelar una reservación con estado '{res['estado']}'"
            )
        
        # Actualizar estado
        update_query = """
            UPDATE reservaciones 
            SET estado = 'cancelada'
            WHERE id = %s
        """
        execute_query(update_query, (reservacion_id,), fetch=False)
        
        print(f" Reservación cancelada exitosamente")
        
        return {
            "message": "Reservación cancelada exitosamente",
            "reservacion_id": reservacion_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error cancelando reservación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sucursales/disponibles")
async def obtener_sucursales_disponibles():
    """Obtener sucursales que aceptan reservaciones"""
    
    try:
        sucursales_query = """
            SELECT DISTINCT s.*
            FROM sucursales s
            JOIN horarios_disponibles h ON s.id = h.sucursal_id
            WHERE s.activa = TRUE AND h.activo = TRUE
            ORDER BY s.nombre
        """
        sucursales = execute_query(sucursales_query)
        
        return {
            "sucursales": [
                {
                    "id": suc['id'],
                    "nombre": suc['nombre'],
                    "direccion": suc['direccion'],
                    "provincia": suc['provincia'],
                    "telefono": suc['telefono']
                }
                for suc in sucursales
            ],
            "total": len(sucursales)
        }
        
    except Exception as e:
        print(f"Error obteniendo sucursales: {e}")
        raise HTTPException(status_code=500, detail=str(e))