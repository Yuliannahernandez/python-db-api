
from fastapi import APIRouter, HTTPException, status, Query
from app.models.profile import UpdateProfileDto, UpdateFotoPerfilDto, CreateDireccionDto, CreateMetodoPagoDto, AddCondicionesSaludDto
from app.config.database import execute_query

router = APIRouter(prefix="/profile", tags=["Profile"])

# ============= PERFIL =============

@router.get("/condiciones-salud")
def get_condiciones_salud():
    """Obtener todas las condiciones de salud disponibles"""
    query = "SELECT * FROM condiciones_salud ORDER BY nombre ASC"
    return execute_query(query)

@router.get("/{usuario_id}")
def get_profile(usuario_id: int):
    query = """
        SELECT 
            c.id,
            c.nombre,
            c.apellido,
            c.edad,
            c.telefono,
            c.idioma,
            c.puntos_lealtad,
            c.foto_perfil,
            c.fecha_nacimiento,
            u.correo
        FROM clientes c
        JOIN usuarios u ON c.usuario_id = u.id
        WHERE c.usuario_id = %s
    """
    result = execute_query(query, (usuario_id,))
    
    if not result:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    
    perfil = result[0]
    return {
        "id": perfil['id'],
        "nombre": perfil['nombre'],
        "apellido": perfil['apellido'],
        "edad": perfil['edad'],
        "telefono": perfil['telefono'],
        "correo": perfil['correo'],
        "idioma": perfil['idioma'],
        "puntos_lealtad": perfil['puntos_lealtad'],
        "foto_perfil": perfil['foto_perfil'],
        "fecha_nacimiento": perfil['fecha_nacimiento'].isoformat() if perfil['fecha_nacimiento'] else None
    }


@router.put("/{usuario_id}")
def update_profile(usuario_id: int, data: UpdateProfileDto):
    # Verificar que el cliente existe
    check_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(check_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    
  
    fields = []
    values = []
    
    if data.nombre is not None:
        fields.append("nombre = %s")
        values.append(data.nombre)
    if data.apellido is not None:
        fields.append("apellido = %s")
        values.append(data.apellido)
    if data.edad is not None:
        fields.append("edad = %s")
        values.append(data.edad)
    if data.telefono is not None:
        fields.append("telefono = %s")
        values.append(data.telefono)
    if data.idioma is not None:
        fields.append("idioma = %s")
        values.append(data.idioma)
    if data.fecha_nacimiento is not None:
        fields.append("fecha_nacimiento = %s")
        values.append(data.fecha_nacimiento)
    
    if fields:
        values.append(usuario_id)
        query = f"UPDATE clientes SET {', '.join(fields)} WHERE usuario_id = %s"
        execute_query(query, tuple(values), fetch=False)
    
    return {
        "message": "Perfil actualizado exitosamente",
        "data": data.dict(exclude_none=True)
    }


@router.put("/{usuario_id}/foto")
def update_foto_perfil(usuario_id: int, data: UpdateFotoPerfilDto):
    query = "UPDATE clientes SET foto_perfil = %s WHERE usuario_id = %s"
    result = execute_query(query, (data.foto_perfil, usuario_id), fetch=False)
    
    if result.get('affected_rows', 0) == 0:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    return {
        "message": "Foto actualizada correctamente",
        "foto_perfil": data.foto_perfil
    }


# ============= DIRECCIONES =============
@router.get("/{usuario_id}/direcciones")
def get_direcciones(usuario_id: int):
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        return []
    
    cliente_id = cliente[0]['id']
    
    query = """
        SELECT * FROM direcciones
        WHERE cliente_id = %s AND activa = TRUE
        ORDER BY es_principal DESC, fecha_creacion DESC
    """
    return execute_query(query, (cliente_id,))


@router.post("/{usuario_id}/direcciones")
def create_direccion(usuario_id: int, data: CreateDireccionDto):
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Si es principal, desmarcar las demás
    if data.es_principal:
        execute_query(
            "UPDATE direcciones SET es_principal = FALSE WHERE cliente_id = %s",
            (cliente_id,),
            fetch=False
        )
    
    # Crear dirección con los campos correctos
    query = """
        INSERT INTO direcciones 
        (cliente_id, alias, direccion_completa, ciudad, provincia, codigo_postal, 
         latitud, longitud, referencia, es_principal)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    result = execute_query(query, (
        cliente_id, 
        data.alias, 
        data.direccion_completa,
        data.ciudad,
        data.provincia, 
        data.codigo_postal,
        data.latitud,
        data.longitud,
        data.referencia,
        data.es_principal
    ), fetch=False)
    
    return {
        "message": "Dirección agregada exitosamente",
        "data": {"id": result['last_id'], **data.dict()}
    }


@router.put("/{usuario_id}/direcciones/{direccion_id}")
def update_direccion(usuario_id: int, direccion_id: int, data: CreateDireccionDto):
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Verificar que la dirección pertenece al cliente
    dir_query = "SELECT id FROM direcciones WHERE id = %s AND cliente_id = %s"
    direccion = execute_query(dir_query, (direccion_id, cliente_id))
    
    if not direccion:
        raise HTTPException(status_code=404, detail="Dirección no encontrada")
    
    # Si es principal, desmarcar las demás
    if data.es_principal:
        execute_query(
            "UPDATE direcciones SET es_principal = FALSE WHERE cliente_id = %s",
            (cliente_id,),
            fetch=False
        )
    
    # Actualizar dirección
    query = """
        UPDATE direcciones 
        SET alias = %s, direccion_completa = %s, ciudad = %s, provincia = %s,
            codigo_postal = %s, latitud = %s, longitud = %s, referencia = %s,
            es_principal = %s
        WHERE id = %s
    """
    execute_query(query, (
        data.alias, 
        data.direccion_completa, 
        data.ciudad,
        data.provincia,
        data.codigo_postal,
        data.latitud,
        data.longitud,
        data.referencia,
        data.es_principal, 
        direccion_id
    ), fetch=False)
    
    return {
        "message": "Dirección actualizada exitosamente",
        "data": data.dict()
    }


@router.delete("/{usuario_id}/direcciones/{direccion_id}")
def delete_direccion(usuario_id: int, direccion_id: int):
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Marcar como inactiva
    query = "UPDATE direcciones SET activa = FALSE WHERE id = %s AND cliente_id = %s"
    result = execute_query(query, (direccion_id, cliente_id), fetch=False)
    
    if result['affected_rows'] == 0:
        raise HTTPException(status_code=404, detail="Dirección no encontrada")
    
    return {"message": "Dirección eliminada exitosamente"}

# ============= CONDICIONES DE SALUD =============


@router.get("/{usuario_id}/condiciones-salud")
def get_cliente_condiciones(usuario_id: int):
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        return []
    
    cliente_id = cliente[0]['id']
    
    # Obtener condiciones del cliente
    query = """
        SELECT cs.id, cs.nombre, cs.descripcion
        FROM cliente_condiciones cc
        JOIN condiciones_salud cs ON cc.condicion_id = cs.id
        WHERE cc.cliente_id = %s
        ORDER BY cs.nombre ASC
    """
    return execute_query(query, (cliente_id,))


@router.post("/{usuario_id}/condiciones-salud")
def add_condiciones_salud(usuario_id: int, data: AddCondicionesSaludDto):
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Eliminar condiciones anteriores
    execute_query(
        "DELETE FROM cliente_condiciones WHERE cliente_id = %s",
        (cliente_id,),
        fetch=False
    )
    
    # Agregar nuevas condiciones
    if data.condicion_ids:
        for condicion_id in data.condicion_ids:
            # Verificar que la condición existe
            verify_query = "SELECT id FROM condiciones_salud WHERE id = %s"
            condicion_existe = execute_query(verify_query, (condicion_id,))
            
            if not condicion_existe:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Condición con id {condicion_id} no existe"
                )
            
            execute_query(
                "INSERT INTO cliente_condiciones (cliente_id, condicion_id) VALUES (%s, %s)",
                (cliente_id, condicion_id),
                fetch=False
            )
    
    return {"message": "Condiciones de salud actualizadas exitosamente"}
# ============= MÉTODOS DE PAGO =============
@router.get("/{usuario_id}/metodos-pago")
def get_metodos_pago(usuario_id: int):
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        return []
    
    cliente_id = cliente[0]['id']
    
    query = """
        SELECT id, cliente_id, tipo, alias, ultimos_digitos, marca, 
               nombre_titular, fecha_expiracion, es_principal, activo, 
               token_pago, fecha_creacion
        FROM metodos_pago
        WHERE cliente_id = %s AND activo = TRUE
        ORDER BY es_principal DESC, fecha_creacion DESC
    """
    
    result = execute_query(query, (cliente_id,))
    
    # Convertir fechas a string
    for metodo in result:
        if metodo.get('fecha_expiracion'):
            metodo['fecha_expiracion'] = str(metodo['fecha_expiracion'])
        if metodo.get('fecha_creacion'):
            metodo['fecha_creacion'] = str(metodo['fecha_creacion'])
    
    return result

@router.post("/{usuario_id}/metodos-pago")
def create_metodo_pago(usuario_id: int, data: CreateMetodoPagoDto):
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Si es principal, desmarcar los demás
    if data.es_principal:
        execute_query(
            "UPDATE metodos_pago SET es_principal = FALSE WHERE cliente_id = %s",
            (cliente_id,),
            fetch=False
        )
    
    # Crear método de pago
    query = """
        INSERT INTO metodos_pago 
        (cliente_id, tipo, alias, ultimos_digitos, marca, nombre_titular, 
         fecha_expiracion, es_principal, token_pago)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    result = execute_query(query, (
        cliente_id, 
        data.tipo, 
        data.alias,
        data.ultimos_digitos, 
        data.marca,
        data.nombre_titular,
        data.fecha_expiracion, 
        data.es_principal,
        data.token_pago
    ), fetch=False)
    
    return {
        "message": "Método de pago agregado exitosamente",
        "data": {"id": result['last_id'], **data.dict()}
    }


@router.put("/{usuario_id}/metodos-pago/{metodo_pago_id}")
def update_metodo_pago(usuario_id: int, metodo_pago_id: int, data: CreateMetodoPagoDto):
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Verificar que el método pertenece al cliente
    mp_query = "SELECT id FROM metodos_pago WHERE id = %s AND cliente_id = %s AND activo = TRUE"
    metodo = execute_query(mp_query, (metodo_pago_id, cliente_id))
    
    if not metodo:
        raise HTTPException(status_code=404, detail="Método de pago no encontrado")
    
    # Si es principal, desmarcar los demás
    if data.es_principal:
        execute_query(
            "UPDATE metodos_pago SET es_principal = FALSE WHERE cliente_id = %s",
            (cliente_id,),
            fetch=False
        )
    
    # Actualizar método de pago
    query = """
        UPDATE metodos_pago 
        SET tipo = %s, alias = %s, ultimos_digitos = %s, marca = %s,
            nombre_titular = %s, fecha_expiracion = %s, es_principal = %s,
            token_pago = %s
        WHERE id = %s
    """
    execute_query(query, (
        data.tipo, 
        data.alias,
        data.ultimos_digitos,
        data.marca,
        data.nombre_titular,
        data.fecha_expiracion, 
        data.es_principal,
        data.token_pago,
        metodo_pago_id
    ), fetch=False)
    
    return {
        "message": "Método de pago actualizado exitosamente",
        "data": data.dict()
    }

@router.delete("/{usuario_id}/metodos-pago/{metodo_pago_id}")
def delete_metodo_pago(usuario_id: int, metodo_pago_id: int):
    # Buscar cliente
    cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
    cliente = execute_query(cliente_query, (usuario_id,))
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    cliente_id = cliente[0]['id']
    
    # Verificar que el método de pago pertenece al cliente antes de eliminar
    verify_query = """
        SELECT id FROM metodos_pago 
        WHERE id = %s AND cliente_id = %s AND activo = TRUE
    """
    metodo = execute_query(verify_query, (metodo_pago_id, cliente_id))
    
    if not metodo:
        raise HTTPException(status_code=404, detail="Método de pago no encontrado")
    
    # Marcar como inactivo 
    query = "UPDATE metodos_pago SET activo = FALSE WHERE id = %s AND cliente_id = %s"
    result = execute_query(query, (metodo_pago_id, cliente_id), fetch=False)
    
    if result.get('affected_rows', 0) == 0:
        raise HTTPException(status_code=404, detail="No se pudo eliminar el método de pago")
    
    return {"message": "Método de pago eliminado exitosamente"}