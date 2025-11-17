from fastapi import APIRouter, HTTPException, status, Query
from app.config.database import execute_query
from typing import Optional
from pydantic import BaseModel
from app.models.usuario import UsuarioCreate
from datetime import datetime, timedelta
import secrets

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("/")
def get_usuarios():
    query = """
        SELECT u.id, u.correo, u.rol, u.estado, u.emailVerified, u.ultimo_acceso,
               c.nombre, c.apellido, c.telefono, c.edad, c.puntos_lealtad, c.idioma
        FROM usuarios u
        LEFT JOIN clientes c ON u.id = c.usuario_id
    """
    return execute_query(query)


@router.get("/{id}")
def get_usuario(id: int):
    query = """
        SELECT u.id, u.correo, u.rol, u.estado, u.emailVerified,
               u.two_fa_secret, u.is_2fa_enabled,
               c.nombre, c.apellido, c.telefono, c.edad, c.fecha_nacimiento,
               c.puntos_lealtad, c.idioma, c.foto_perfil
        FROM usuarios u
        LEFT JOIN clientes c ON u.id = c.usuario_id
        WHERE u.id = %s
    """
    result = execute_query(query, (id,))
    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return result[0]


@router.get("/email/{correo}")
def get_usuario_by_email(correo: str):
    query = """
        SELECT u.*, c.nombre, c.apellido, c.telefono, c.edad, c.puntos_lealtad
               
        FROM usuarios u
        LEFT JOIN clientes c ON u.id = c.usuario_id
        WHERE u.correo = %s
    """
    result = execute_query(query, (correo,))
    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return result[0]


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_usuario(usuario: UsuarioCreate):
    verification_token = secrets.token_hex(32)
    verification_expiry = datetime.utcnow() + timedelta(hours=24)

   
    verification_expiry_str = verification_expiry.strftime('%Y-%m-%d %H:%M:%S')

  
    query_usuario = """
        INSERT INTO usuarios 
        (correo, password_hash, rol, estado, emailVerified, is_google_auth, 
         verificationToken, verificationTokenExpiry)
        VALUES (%s, %s, %s, 'activo', FALSE, FALSE, %s, %s)
    """
    result = execute_query(
        query_usuario,
        (
            usuario.correo,
            usuario.password_Hash,
            usuario.rol,
            verification_token,
            verification_expiry_str  
        ),
        fetch=False
    )
    usuario_id = result['last_id']

    # Crear cliente si aplica
    if usuario.rol == 'cliente':
        query_cliente = """
            INSERT INTO clientes (usuario_id, nombre, apellido, telefono, edad, idioma, puntos_lealtad)
            VALUES (%s, %s, %s, %s, %s, 'es', 0)
        """
        execute_query(
            query_cliente,
            (usuario_id, usuario.nombre, usuario.apellido, usuario.telefono, usuario.edad),
            fetch=False
        )

    return {
        "id": usuario_id,
        "verification_token": verification_token,
        "verification_expiry": verification_expiry,
        **usuario.dict()
    }


# ============= BÚSQUEDA POR TOKEN DE VERIFICACIÓN =============
@router.get("/verification-token/{token}")
def get_usuario_by_verification_token(token: str):
    """Busca un usuario por su token de verificación"""
    query = """
        SELECT u.id, u.correo, u.rol, u.estado, u.emailVerified,
               u.verificationToken, u.verificationTokenExpiry,
               c.nombre, c.apellido, c.telefono, c.edad, c.puntos_lealtad
        FROM usuarios u
        LEFT JOIN clientes c ON u.id = c.usuario_id
        WHERE u.verificationToken = %s
    """
    result = execute_query(query, (token,))
    
    if not result:
        raise HTTPException(
            status_code=404, 
            detail=f"Token de verificación no encontrado"
        )
    
    usuario = result[0]
    
    # Verificar si el token ha expirado
    if usuario.get('verificationTokenExpiry'):
        expiry = usuario['verificationTokenExpiry']
        if isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
        
        if datetime.utcnow() > expiry:
            raise HTTPException(
                status_code=400,
                detail="El token de verificación ha expirado"
            )
    
    return usuario


# ============= BÚSQUEDA POR TOKEN DE RECUPERACIÓN =============
@router.get("/recovery-token/{token}")
def get_usuario_by_recovery_token(token: str):
    """Busca un usuario por su token de recuperación de contraseña"""
    query = """
        SELECT u.id, u.correo, u.rol, u.estado, u.emailVerified,
               u.token_recuperacion, u.token_expiracion,
               c.nombre, c.apellido, c.telefono, c.edad, c.puntos_lealtad
        FROM usuarios u
        LEFT JOIN clientes c ON u.id = c.usuario_id
        WHERE u.token_recuperacion = %s
    """
    result = execute_query(query, (token,))
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Token de recuperación no encontrado"
        )
    
    usuario = result[0]
    
    # Verificar si el token ha expirado
    if usuario.get('token_expiracion'):
        expiry = usuario['token_expiracion']
        if isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
        
        if datetime.utcnow() > expiry:
            raise HTTPException(
                status_code=400,
                detail="El token de recuperación ha expirado"
            )
    
    return usuario


# ============= BÚSQUEDA POR TELÉFONO =============
@router.get("/by-phone/{telefono}")
def get_usuario_by_phone(telefono: str):
    query = """
        SELECT u.*, c.nombre, c.apellido, c.telefono, c.puntos_lealtad
        FROM usuarios u
        LEFT JOIN clientes c ON u.id = c.usuario_id
        WHERE c.telefono = %s
    """
    result = execute_query(query, (telefono,))
    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return result[0]


# ============= BÚSQUEDA POR NOMBRE Y APELLIDO =============
@router.get("/by-name")
def get_usuario_by_name(nombre: str = Query(...), apellido: str = Query(...)):
    query = """
        SELECT u.*, c.nombre, c.apellido, c.telefono, c.puntos_lealtad
        FROM usuarios u
        LEFT JOIN clientes c ON u.id = c.usuario_id
        WHERE c.nombre = %s AND c.apellido = %s
    """
    result = execute_query(query, (nombre, apellido))
    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return result[0]


# ============= ACTUALIZAR ÚLTIMO ACCESO =============
@router.put("/{id}/ultimo-acceso")
def update_ultimo_acceso(id: int):
    query = """
        UPDATE usuarios 
        SET ultimo_acceso = NOW() 
        WHERE id = %s
    """
    execute_query(query, (id,), fetch=False)
    return {"message": "Último acceso actualizado", "id": id}


# ============= MODELO PARA ACTUALIZACIÓN COMPLETA DE USUARIO =============
class UsuarioFullUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    telefono: Optional[str] = None
    edad: Optional[int] = None
    password_hash: Optional[str] = None
    emailVerified: Optional[bool] = None
    verificationToken: Optional[str] = None
    verificationTokenExpiry: Optional[str] = None
    token_recuperacion: Optional[str] = None
    token_expiracion: Optional[str] = None
    two_fa_secret: Optional[str] = None
    is_2fa_enabled: Optional[bool] = None
    ultimo_acceso: Optional[str] = None
    estado: Optional[str] = None


# ============= ACTUALIZAR USUARIO COMPLETO =============
@router.put("/{id}")
def update_usuario_full(id: int, usuario: UsuarioFullUpdate):
    # Actualizar tabla usuarios
    usuario_fields = []
    usuario_values = []

    if usuario.password_hash:
        usuario_fields.append("password_hash = %s")
        usuario_values.append(usuario.password_hash)
    if usuario.emailVerified is not None:
        usuario_fields.append("emailVerified = %s")
        usuario_values.append(usuario.emailVerified)
    if usuario.verificationToken is not None:
        usuario_fields.append("verificationToken = %s")
        usuario_values.append(usuario.verificationToken)
    if usuario.verificationTokenExpiry:
        usuario_fields.append("verificationTokenExpiry = %s")
        usuario_values.append(usuario.verificationTokenExpiry)
    if usuario.token_recuperacion is not None:
        usuario_fields.append("token_recuperacion = %s")
        usuario_values.append(usuario.token_recuperacion)
    if usuario.token_expiracion:
        usuario_fields.append("token_expiracion = %s")
        usuario_values.append(usuario.token_expiracion)
    if usuario.two_fa_secret is not None:
        usuario_fields.append("two_fa_secret = %s")
        usuario_values.append(usuario.two_fa_secret)
    if usuario.is_2fa_enabled is not None:
        usuario_fields.append("is_2fa_enabled = %s")
        usuario_values.append(usuario.is_2fa_enabled)
    if usuario.ultimo_acceso:
        usuario_fields.append("ultimo_acceso = %s")
        usuario_values.append(usuario.ultimo_acceso)
    if usuario.estado:
        usuario_fields.append("estado = %s")
        usuario_values.append(usuario.estado)

    if usuario_fields:
        usuario_values.append(id)
        query = f"UPDATE usuarios SET {', '.join(usuario_fields)} WHERE id = %s"
        execute_query(query, tuple(usuario_values), fetch=False)

    # Actualizar tabla clientes
    cliente_fields = []
    cliente_values = []

    if usuario.nombre:
        cliente_fields.append("nombre = %s")
        cliente_values.append(usuario.nombre)
    if usuario.apellido:
        cliente_fields.append("apellido = %s")
        cliente_values.append(usuario.apellido)
    if usuario.telefono:
        cliente_fields.append("telefono = %s")
        cliente_values.append(usuario.telefono)
    if usuario.edad:
        cliente_fields.append("edad = %s")
        cliente_values.append(usuario.edad)

    if cliente_fields:
        cliente_values.append(id)
        query = f"UPDATE clientes SET {', '.join(cliente_fields)} WHERE usuario_id = %s"
        execute_query(query, tuple(cliente_values), fetch=False)

    return {"message": "Usuario actualizado", "id": id}