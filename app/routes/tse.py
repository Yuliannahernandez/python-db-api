# python-db-api/app/routes/tse.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import random

router = APIRouter(
    prefix="/tse",
    tags=["TSE - Tribunal Supremo de Elecciones"]
)

class ValidarCedulaRequest(BaseModel):
    numero_cedula: str


CEDULAS_SIMULADAS = {
    "101110111": {
        "nombre": "JUAN CARLOS",
        "apellido1": "RODRIGUEZ",
        "apellido2": "MORA",
        "fecha_nacimiento": "1985-03-15",
        "provincia": "San José",
        "canton": "Central",
        "distrito": "Carmen",
        "nacionalidad": "Costarricense",
        "estado_civil": "Casado",
        "sexo": "M",
        "fecha_vencimiento": "2028-12-31",
        "valida": True
    },
    "102220222": {
        "nombre": "MARIA JOSE",
        "apellido1": "GONZALEZ",
        "apellido2": "SOLANO",
        "fecha_nacimiento": "1990-07-22",
        "provincia": "Cartago",
        "canton": "Cartago",
        "distrito": "Oriental",
        "nacionalidad": "Costarricense",
        "estado_civil": "Soltera",
        "sexo": "F",
        "fecha_vencimiento": "2027-06-30",
        "valida": True
    },
    "203330333": {
        "nombre": "CARLOS ALBERTO",
        "apellido1": "FERNANDEZ",
        "apellido2": "CASTRO",
        "fecha_nacimiento": "1978-11-08",
        "provincia": "Alajuela",
        "canton": "Alajuela",
        "distrito": "Alajuela",
        "nacionalidad": "Costarricense",
        "estado_civil": "Divorciado",
        "sexo": "M",
        "fecha_vencimiento": "2026-03-15",
        "valida": True
    },
    "304440444": {
        "nombre": "ANA PATRICIA",
        "apellido1": "RAMIREZ",
        "apellido2": "VARGAS",
        "fecha_nacimiento": "1995-02-14",
        "provincia": "Heredia",
        "canton": "Heredia",
        "distrito": "Heredia",
        "nacionalidad": "Costarricense",
        "estado_civil": "Soltera",
        "sexo": "F",
        "fecha_vencimiento": "2029-08-20",
        "valida": True
    },
    "405550555": {
        "nombre": "LUIS FERNANDO",
        "apellido1": "JIMENEZ",
        "apellido2": "QUESADA",
        "fecha_nacimiento": "1982-09-30",
        "provincia": "Guanacaste",
        "canton": "Liberia",
        "distrito": "Liberia",
        "nacionalidad": "Costarricense",
        "estado_civil": "Casado",
        "sexo": "M",
        "fecha_vencimiento": "2025-12-31",
        "valida": False  # Cédula vencida
    },
    "506660666": {
        "nombre": "SOFIA ALEJANDRA",
        "apellido1": "MORA",
        "apellido2": "VILLALOBOS",
        "fecha_nacimiento": "1988-05-18",
        "provincia": "Puntarenas",
        "canton": "Puntarenas",
        "distrito": "Puntarenas",
        "nacionalidad": "Costarricense",
        "estado_civil": "Unión Libre",
        "sexo": "F",
        "fecha_vencimiento": "2028-04-15",
        "valida": True
    },
    "607770777": {
        "nombre": "DIEGO ANDRES",
        "apellido1": "SOLIS",
        "apellido2": "MONTERO",
        "fecha_nacimiento": "1992-12-03",
        "provincia": "Limón",
        "canton": "Limón",
        "distrito": "Limón",
        "nacionalidad": "Costarricense",
        "estado_civil": "Soltero",
        "sexo": "M",
        "fecha_vencimiento": "2030-01-10",
        "valida": True
    },
    # Cédulas de extranjeros (formato diferente)
    "800001234567": {
        "nombre": "JOHN MICHAEL",
        "apellido1": "SMITH",
        "apellido2": "",
        "fecha_nacimiento": "1980-01-01",
        "provincia": "San José",
        "canton": "Escazú",
        "distrito": "Escazú",
        "nacionalidad": "Estadounidense",
        "estado_civil": "Casado",
        "sexo": "M",
        "tipo": "Residente",
        "fecha_vencimiento": "2026-12-31",
        "valida": True
    },
    "999999999": {
        "nombre": "INVALIDA",
        "apellido1": "CEDULA",
        "apellido2": "INVALIDA",
        "fecha_nacimiento": "2000-01-01",
        "provincia": "N/A",
        "canton": "N/A",
        "distrito": "N/A",
        "nacionalidad": "N/A",
        "estado_civil": "N/A",
        "sexo": "N/A",
        "fecha_vencimiento": "2000-01-01",
        "valida": False
    }
}

def validar_formato_cedula(cedula: str) -> dict:
    """Validar formato de cédula costarricense"""
    
    # Remover espacios y guiones
    cedula = cedula.replace(' ', '').replace('-', '')
    
    # Verificar que sea solo números
    if not cedula.isdigit():
        return {
            "valido": False,
            "mensaje": "La cédula debe contener solo números"
        }
    
    # Cédula física (9 dígitos) - Formato: 0-0000-0000
    if len(cedula) == 9:
        provincia = int(cedula[0])
        if provincia < 1 or provincia > 9:
            return {
                "valido": False,
                "mensaje": "Provincia inválida (primer dígito debe ser 1-9)"
            }
        return {
            "valido": True,
            "tipo": "Cédula Física",
            "formato": f"{cedula[0]}-{cedula[1:5]}-{cedula[5:9]}"
        }
    
    # Cédula de residencia (11 o 12 dígitos)
    elif len(cedula) in [11, 12]:
        return {
            "valido": True,
            "tipo": "Cédula de Residencia",
            "formato": cedula
        }
    
    # DIMEX (11 o 12 dígitos)
    elif len(cedula) >= 11:
        return {
            "valido": True,
            "tipo": "DIMEX",
            "formato": cedula
        }
    
    return {
        "valido": False,
        "mensaje": "Longitud de cédula inválida"
    }

@router.post("/validar-cedula")
async def validar_cedula(request: ValidarCedulaRequest):
    """Validar cédula contra el sistema del TSE (simulado)"""
    
    try:
        cedula = request.numero_cedula.replace(' ', '').replace('-', '')
        
        print(f"🇨🇷 Validando cédula TSE: {cedula}")
        
        # 1. Validar formato
        validacion_formato = validar_formato_cedula(cedula)
        
        if not validacion_formato["valido"]:
            return {
                "valida": False,
                "mensaje": validacion_formato["mensaje"],
                "datos": None
            }
        
        
        import time
        time.sleep(0.5)  
        
        # 3. Buscar en base de datos simulada
        if cedula in CEDULAS_SIMULADAS:
            datos = CEDULAS_SIMULADAS[cedula]
            
            # Verificar si la cédula está vencida
            fecha_venc = datetime.strptime(datos['fecha_vencimiento'], '%Y-%m-%d')
            vencida = fecha_venc < datetime.now()
            
            if vencida and datos['valida']:
                return {
                    "valida": False,
                    "mensaje": "Cédula vencida",
                    "datos": {
                        **datos,
                        "formato_cedula": validacion_formato["formato"],
                        "tipo_documento": validacion_formato["tipo"]
                    }
                }
            
            if not datos['valida']:
                return {
                    "valida": False,
                    "mensaje": "Cédula inválida o cancelada",
                    "datos": None
                }
            
            # Calcular edad
            fecha_nac = datetime.strptime(datos['fecha_nacimiento'], '%Y-%m-%d')
            edad = (datetime.now() - fecha_nac).days // 365
            
            print(f"Cédula válida: {datos['nombre']} {datos['apellido1']} {datos['apellido2']}")
            
            return {
                "valida": True,
                "mensaje": "Cédula válida",
                "datos": {
                    "numero_cedula": cedula,
                    "formato_cedula": validacion_formato["formato"],
                    "tipo_documento": validacion_formato["tipo"],
                    "nombre_completo": f"{datos['nombre']} {datos['apellido1']} {datos['apellido2']}".strip(),
                    "nombre": datos['nombre'],
                    "apellido1": datos['apellido1'],
                    "apellido2": datos['apellido2'],
                    "fecha_nacimiento": datos['fecha_nacimiento'],
                    "edad": edad,
                    "provincia": datos['provincia'],
                    "canton": datos['canton'],
                    "distrito": datos['distrito'],
                    "nacionalidad": datos['nacionalidad'],
                    "estado_civil": datos['estado_civil'],
                    "sexo": datos['sexo'],
                    "fecha_vencimiento": datos['fecha_vencimiento']
                }
            }
        else:
            # Generar datos aleatorios para cédulas no registradas
            print(f" Cédula no encontrada en BD simulada, generando datos...")
            
            nombres_m = ["JOSE", "CARLOS", "JUAN", "LUIS", "DIEGO", "ANDRES", "MIGUEL", "FERNANDO"]
            nombres_f = ["MARIA", "ANA", "SOFIA", "CARMEN", "LAURA", "PATRICIA", "GABRIELA", "DANIELA"]
            apellidos = ["RODRIGUEZ", "GONZALEZ", "RAMIREZ", "FERNANDEZ", "JIMENEZ", "MORA", "CASTRO", "VARGAS"]
            provincias = ["San José", "Alajuela", "Cartago", "Heredia", "Guanacaste", "Puntarenas", "Limón"]
            
            sexo = "M" if random.random() > 0.5 else "F"
            nombre = random.choice(nombres_m if sexo == "M" else nombres_f)
            apellido1 = random.choice(apellidos)
            apellido2 = random.choice(apellidos)
            provincia = random.choice(provincias)
            
            return {
                "valida": True,
                "mensaje": "Cédula válida (datos simulados)",
                "datos": {
                    "numero_cedula": cedula,
                    "formato_cedula": validacion_formato["formato"],
                    "tipo_documento": validacion_formato["tipo"],
                    "nombre_completo": f"{nombre} {apellido1} {apellido2}",
                    "nombre": nombre,
                    "apellido1": apellido1,
                    "apellido2": apellido2,
                    "fecha_nacimiento": "1990-01-01",
                    "edad": 34,
                    "provincia": provincia,
                    "canton": provincia,
                    "distrito": provincia,
                    "nacionalidad": "Costarricense",
                    "estado_civil": "Soltero",
                    "sexo": sexo,
                    "fecha_vencimiento": "2028-12-31"
                }
            }
        
    except Exception as e:
        print(f"Error validando cédula: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cedulas-prueba")
async def obtener_cedulas_prueba():
    """Obtener lista de cédulas de prueba"""
    
    return {
        "cedulas_prueba": [
            {
                "numero": "1-0111-0111",
                "nombre": "Juan Carlos Rodríguez Mora",
                "provincia": "San José",
                "estado": "Válida",
                "descripcion": "Cédula física válida"
            },
            {
                "numero": "1-0222-0222",
                "nombre": "María José González Solano",
                "provincia": "Cartago",
                "estado": "Válida",
                "descripcion": "Cédula física válida"
            },
            {
                "numero": "2-0333-0333",
                "nombre": "Carlos Alberto Fernández Castro",
                "provincia": "Alajuela",
                "estado": "Válida",
                "descripcion": "Cédula física válida"
            },
            {
                "numero": "4-0555-0555",
                "nombre": "Luis Fernando Jiménez Quesada",
                "provincia": "Guanacaste",
                "estado": "Vencida",
                "descripcion": "Cédula vencida - Para probar rechazo"
            },
            {
                "numero": "9-9999-9999",
                "nombre": "Inválida Cédula Inválida",
                "provincia": "N/A",
                "estado": "Inválida",
                "descripcion": "Cédula inválida - Para probar rechazo"
            },
            {
                "numero": "800001234567",
                "nombre": "John Michael Smith",
                "provincia": "San José",
                "estado": "Válida",
                "descripcion": "Cédula de extranjero residente"
            }
        ],
        "nota": "Estas son cédulas simuladas para pruebas del TSE de Costa Rica",
        "formato": {
            "cedula_fisica": "X-XXXX-XXXX (9 dígitos)",
            "cedula_residencia": "XXXXXXXXXXXX (11-12 dígitos)",
            "dimex": "XXXXXXXXXXXX (11-12 dígitos)"
        }
    }