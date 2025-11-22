# app/routes/recomendaciones.py
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from app.config.database import execute_query
import random

router = APIRouter(
    prefix="/recomendaciones",
    tags=["Recomendaciones"]
)

class PeliculaRecomendacion(BaseModel):
    titulo: str
    año: int
    genero: str
    sinopsis: str
    poster: str
    rating: float
    razon: str  # Por qué se recomienda según la comida

# Mapeo de categorías de comida a películas
RECOMENDACIONES_POR_COMIDA = {
    "pizza": [
        {
            "titulo": "Ratatouille",
            "año": 2007,
            "genero": "Animación, Comedia",
            "sinopsis": "Una rata con sueños de convertirse en chef en un restaurante parisino de primer nivel.",
            "poster": "https://i.pinimg.com/736x/eb/bf/28/ebbf28303696dd50ccc1a9738bd90556.jpg",
            "rating": 8.1,
            "razon": "Perfecta para disfrutar mientras saboreas tu pizza. Una historia culinaria inspiradora."
        },
        {
            "titulo": "Chef",
            "año": 2014,
            "genero": "Comedia, Drama",
            "sinopsis": "Un chef que pierde su trabajo en un restaurante de Los Ángeles inicia un food truck.",
            "poster": "https://image.tmdb.org/t/p/w500/jOl4SbqqOIGEbOOUEebUMiGCsgr.jpg",
            "rating": 7.3,
            "razon": "Comida callejera deliciosa y pasión por la cocina. Ideal con tu pizza."
        },
        {
            "titulo": "Mystic Pizza",
            "año": 1988,
            "genero": "Romance, Drama",
            "sinopsis": "Tres jóvenes camareras en una pizzería de Connecticut buscan el amor y la identidad.",
            "poster": "https://image.tmdb.org/t/p/w500/8Q7sR9kY0l5o0VrYcGbKqNLqPRF.jpg",
            "rating": 6.3,
            "razon": "¡Una película clásica sobre una pizzería! La combinación perfecta."
        }
    ],
    "hamburguesa": [
        {
            "titulo": "The Founder",
            "año": 2016,
            "genero": "Biografía, Drama",
            "sinopsis": "La historia de Ray Kroc y cómo transformó McDonald's en el imperio de fast food más grande.",
            "poster": "https://image.tmdb.org/t/p/w500/kBJJJwRXZA5qzyOq73F4TcpEHhP.jpg",
            "rating": 7.2,
            "razon": "La historia detrás del imperio de las hamburguesas. Fascinante mientras comes."
        },
        {
            "titulo": "Pulp Fiction",
            "año": 1994,
            "genero": "Crimen, Drama",
            "sinopsis": "Historias entrelazadas de crimen y redención en Los Ángeles.",
            "poster": "https://image.tmdb.org/t/p/w500/dM2w364MScsjFf8pfMbaWUcWrR.jpg",
            "rating": 8.9,
            "razon": "La icónica escena de la hamburguesa Big Kahuna hace perfecta esta combinación."
        },
        {
            "titulo": "Good Burger",
            "año": 1997,
            "genero": "Comedia, Familiar",
            "sinopsis": "Dos adolescentes trabajan en un restaurante de hamburguesas para salvarlo de la competencia.",
            "poster": "https://image.tmdb.org/t/p/w500/rGVyQUXmp27GvfEZb6zLvjHKkNj.jpg",
            "rating": 5.8,
            "razon": "Comedia divertida y ligera, perfecta con tu hamburguesa."
        }
    ],
    "pasta": [
        {
            "titulo": "The Godfather",
            "año": 1972,
            "genero": "Crimen, Drama",
            "sinopsis": "La saga de la familia Corleone bajo el patriarca Vito Corleone.",
            "poster": "https://image.tmdb.org/t/p/w500/3bhkrj58Vtu7enYsRolD1fZdja1.jpg",
            "rating": 9.2,
            "razon": "Clásico italiano por excelencia. La escena de la cena con pasta es legendaria."
        },
        {
            "titulo": "Julie & Julia",
            "año": 2009,
            "genero": "Biografía, Romance",
            "sinopsis": "Dos mujeres, una en los 50s y otra moderna, encuentran realización a través de la cocina.",
            "poster": "https://i.pinimg.com/736x/d5/16/b8/d516b82a5adb5edd03c60f5660564c48.jpg",
            "rating": 7.0,
            "razon": "Amor por la cocina francesa e italiana. Perfecta para disfrutar con pasta."
        },
        {
            "titulo": "Eat Pray Love",
            "año": 2010,
            "genero": "Romance, Drama",
            "sinopsis": "Una mujer viaja por Italia, India e Indonesia buscando el equilibrio en su vida.",
            "poster": "https://image.tmdb.org/t/p/w500/9Hgiv1UEIjc8VwtOmFBCFzMs0er.jpg",
            "rating": 5.8,
            "razon": "El segmento en Italia celebra la pasta y la comida italiana. Inspirador."
        }
    ],
    "sushi": [
        {
            "titulo": "Jiro Dreams of Sushi",
            "año": 2011,
            "genero": "Documental",
            "sinopsis": "La historia de Jiro Ono, maestro del sushi de 85 años y su restaurante de 3 estrellas Michelin.",
            "poster": "https://image.tmdb.org/t/p/w500/7b7NI4SFqgLCGGP5vZoEv1xYKEJ.jpg",
            "rating": 7.9,
            "razon": "El documental perfecto sobre sushi. Arte culinario en su máxima expresión."
        },
        {
            "titulo": "The Wolverine",
            "año": 2013,
            "genero": "Acción, Ciencia Ficción",
            "sinopsis": "Wolverine viaja a Japón donde enfrenta su mortalidad.",
            "poster": "https://image.tmdb.org/t/p/w500/xNi8daRmN4XY8rXHd4rwLbJf1cU.jpg",
            "rating": 6.7,
            "razon": "Ambientada en Japón con escenas hermosas de cultura japonesa y comida."
        },
        {
            "titulo": "Lost in Translation",
            "año": 2003,
            "genero": "Romance, Drama",
            "sinopsis": "Dos estadounidenses forman un vínculo en Tokio.",
            "poster": "https://image.tmdb.org/t/p/w500/wv9VQ0JKuPZ3MNqKvL8y3qI8VBQ.jpg",
            "rating": 7.7,
            "razon": "Bellamente filmada en Tokio. Muestra la cultura y gastronomía japonesa."
        }
    ],
    "tacos": [
        {
            "titulo": "Coco",
            "año": 2017,
            "genero": "Animación, Familiar",
            "sinopsis": "Un joven músico viaja a la tierra de los muertos durante el Día de Muertos.",
            "poster": "https://image.tmdb.org/t/p/w500/gGEsBPAijhVUFoiNpgZXqRVWJt2.jpg",
            "rating": 8.4,
            "razon": "Celebración de la cultura mexicana, su comida y tradiciones. Perfecta con tacos."
        },
        {
            "titulo": "Nacho Libre",
            "año": 2006,
            "genero": "Comedia, Familiar",
            "sinopsis": "Un monje se convierte en luchador para ganar dinero para el orfanato.",
            "poster": "https://image.tmdb.org/t/p/w500/mFdiyu6X7cMW3qQngvAGGi7hOVC.jpg",
            "rating": 5.9,
            "razon": "Comedia ambientada en México. Divertida y llena de referencias culturales."
        },
        {
            "titulo": "Y Tu Mamá También",
            "año": 2001,
            "genero": "Drama, Romance",
            "sinopsis": "Dos adolescentes y una mujer española hacen un viaje por carretera por México.",
            "poster": "https://image.tmdb.org/t/p/w500/8BVl2Hc9PFUw09KlY1XkGhF4Y3o.jpg",
            "rating": 7.7,
            "razon": "Road trip por México mostrando su cultura, paisajes y gastronomía."
        }
    ],
    "pollo": [
        {
            "titulo": "Chicken Run",
            "año": 2000,
            "genero": "Animación, Comedia",
            "sinopsis": "Gallinas intentan escapar de una granja antes de terminar como pasteles.",
            "poster": "https://image.tmdb.org/t/p/w500/tNr89pfGV9FMDczLgGCisVWNHtW.jpg",
            "rating": 7.0,
            "razon": "Divertida animación sobre pollos. Irónica pero entretenida con tu pollo."
        },
        {
            "titulo": "Soul",
            "año": 2020,
            "genero": "Animación, Comedia",
            "sinopsis": "Un músico de jazz explora el significado de la vida.",
            "poster": "https://image.tmdb.org/t/p/w500/kf456ZqeC45XTvo6W9pW5clYKfQ.jpg",
            "rating": 8.0,
            "razon": "Conmovedora historia sobre encontrar tu propósito. Perfecta para una comida relajante."
        },
        {
            "titulo": "Fried Green Tomatoes",
            "año": 1991,
            "genero": "Drama, Comedia",
            "sinopsis": "Historias de amistad entre mujeres en Alabama.",
            "poster": "https://image.tmdb.org/t/p/w500/kJwmwOXOZ6DazThXkKvfDhB1M7D.jpg",
            "rating": 7.7,
            "razon": "Comida sureña y amistad. El Whistle Stop Cafe es icónico."
        }
    ],
    "ensalada": [
        {
            "titulo": "Julie & Julia",
            "año": 2009,
            "genero": "Biografía, Romance",
            "sinopsis": "Dos mujeres encuentran realización a través de la cocina.",
            "poster": "https://i.pinimg.com/736x/d5/16/b8/d516b82a5adb5edd03c60f5660564c48.jpg",
            "rating": 7.0,
            "razon": "Celebra la cocina saludable y el amor por los ingredientes frescos."
        },
        {
            "titulo": "Cloudy with a Chance of Meatballs",
            "año": 2009,
            "genero": "Animación, Comedia",
            "sinopsis": "Un científico inventa una máquina que convierte agua en comida.",
            "poster": "https://image.tmdb.org/t/p/w500/qhOhIKf7QEyPK0UMq5fQe1eAIR.jpg",
            "rating": 6.9,
            "razon": "Comida cayendo del cielo, incluyendo vegetales gigantes. Divertida y colorida."
        }
    ],
    "postre": [
        {
            "titulo": "Chocolat",
            "año": 2000,
            "genero": "Romance, Drama",
            "sinopsis": "Una mujer abre una chocolatería en un pueblo francés conservador.",
            "poster": "https://i.pinimg.com/1200x/30/c7/19/30c71960576cd71dd37293c9c70ab8dd.jpg",
            "rating": 7.2,
            "razon": "Deliciosa película sobre chocolate y pasión. Perfecta con tu postre."
        },
        {
            "titulo": "Willy Wonka & the Chocolate Factory",
            "año": 1971,
            "genero": "Familiar, Fantasía",
            "sinopsis": "Niños visitan la misteriosa fábrica de chocolate de Willy Wonka.",
            "poster": "https://i.pinimg.com/1200x/03/e9/6b/03e96b9c0f20b16c913035c375943915.jpg",
            "rating": 7.8,
            "razon": "Mundo mágico de dulces y chocolate. Nostalgia pura."
        },
        {
            "titulo": "Charlie and the Chocolate Factory",
            "año": 2005,
            "genero": "Aventura, Comedia",
            "sinopsis": "Versión de Tim Burton del clásico cuento de Roald Dahl.",
            "poster": "https://image.tmdb.org/t/p/w500/wfGfxtBkhBzQfOZw4S8IQZgrH0a.jpg",
            "rating": 6.7,
            "razon": "Aventura visual llena de dulces y fantasía."
        }
    ],
    "default": [
        {
            "titulo": "Ratatouille",
            "año": 2007,
            "genero": "Animación, Comedia",
            "sinopsis": "Una rata con sueños de convertirse en chef.",
            "poster": "https://i.pinimg.com/736x/eb/bf/28/ebbf28303696dd50ccc1a9738bd90556.jpg",
            "rating": 8.1,
            "razon": "Una hermosa celebración de la comida y la pasión culinaria."
        },
        {
            "titulo": "Chef",
            "año": 2014,
            "genero": "Comedia, Drama",
            "sinopsis": "Un chef reinventa su carrera con un food truck.",
            "poster": "https://i.pinimg.com/736x/4c/56/eb/4c56ebab27336d28db0b2797f501e4bb.jpg",
            "rating": 7.3,
            "razon": "Inspiradora historia sobre redescubrir tu pasión por la cocida."
        }
    ]
}

def categorizar_producto(nombre_producto: str) -> str:
    
    nombre_lower = nombre_producto.lower()
    
    categorias = {
        "pasta": [
            "pasta", "spaghetti", "espagueti", "trenette", "pesto", 
            "ratatouille",  
            "dama", "vagabundo", "luca"
        ],
        "hamburguesa": [
            "hamburguesa", "burger", "kahuna", "royale", "queso"
        ],
        "postre": [
            "postre", "beignets", "grey stuff", "strudel", "tiana",
            "azúcar", "dulce", "pastel"
        ],
        "pizza": [
            "pizza"
        ],
        "ensalada": [
            "ensalada", "salad"
        ],
        "sushi": [
            "sushi", "roll"
        ],
        "tacos": [
            "taco", "burrito", "quesadilla"
        ],
        "pollo": [
            "pollo", "chicken", "alitas"
        ]
    }
    
    # Buscar coincidencias
    for categoria, palabras_clave in categorias.items():
        for palabra in palabras_clave:
            if palabra in nombre_lower:
                return categoria
    
    return "default"


@router.get("/por-carrito/{usuario_id}")
async def obtener_recomendaciones_carrito(usuario_id: int):
    """Obtener recomendaciones de películas basadas en el carrito actual del usuario"""
    
    try:
        # 1. Buscar cliente
        cliente_query = "SELECT id FROM clientes WHERE usuario_id = %s"
        cliente = execute_query(cliente_query, (usuario_id,))
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        cliente_id = cliente[0]['id']
        
        # 2. Obtener carrito activo
        carrito_query = """
            SELECT id FROM pedidos 
            WHERE cliente_id = %s AND estado = 'carrito'
            ORDER BY fecha_creacion DESC 
            LIMIT 1
        """
        carrito = execute_query(carrito_query, (cliente_id,))
        
        if not carrito:
            return {
                "recomendaciones": RECOMENDACIONES_POR_COMIDA["default"],
                "categoria": "default",
                "mensaje": "Recomendaciones generales. ¡Agrega productos para recomendaciones personalizadas!"
            }
        
        carrito_id = carrito[0]['id']
        
        # 3. Obtener productos del carrito CON SU CATEGORÍA 
        productos_query = """
            SELECT p.nombre, p.categoria, pd.cantidad
            FROM pedido_detalles pd
            JOIN productos p ON pd.producto_id = p.id
            WHERE pd.pedido_id = %s
        """
        productos = execute_query(productos_query, (carrito_id,))
        
        if not productos:
            return {
                "recomendaciones": RECOMENDACIONES_POR_COMIDA["default"],
                "categoria": "default",
                "mensaje": "Tu carrito está vacío. ¡Agrega productos para recomendaciones personalizadas!"
            }
        
        # 4. Contar productos por categoría 
        categorias_encontradas = {}
        for producto in productos:
            categoria = producto.get('categoria', 'default') or 'default'  
            if categoria not in categorias_encontradas:
                categorias_encontradas[categoria] = 0
            categorias_encontradas[categoria] += producto['cantidad']
        
        # 5. Obtener categoría principal (la que tiene más productos)
        categoria_principal = max(categorias_encontradas, key=categorias_encontradas.get)
        
        # 6. Obtener recomendaciones de películas
        peliculas = RECOMENDACIONES_POR_COMIDA.get(categoria_principal, RECOMENDACIONES_POR_COMIDA["default"])
        
        # Mezclar aleatoriamente y tomar 3
        peliculas_seleccionadas = random.sample(peliculas, min(3, len(peliculas)))
        
        return {
            "recomendaciones": peliculas_seleccionadas,
            "categoria": categoria_principal,
            "productos_analizados": len(productos),
            "mensaje": f"Recomendaciones basadas en tu selección de {categoria_principal}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error obteniendo recomendaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/por-pedido/{pedido_id}")
async def obtener_recomendaciones_pedido(pedido_id: int):
    """Obtener recomendaciones basadas en un pedido específico"""
    
    try:
        # Obtener productos del pedido CON CATEGORÍA
        productos_query = """
            SELECT p.nombre, p.categoria, pd.cantidad
            FROM pedido_detalles pd
            JOIN productos p ON pd.producto_id = p.id
            WHERE pd.pedido_id = %s
        """
        productos = execute_query(productos_query, (pedido_id,))
        
        if not productos:
            return {
                "recomendaciones": RECOMENDACIONES_POR_COMIDA["default"],
                "categoria": "default",
                "mensaje": "Recomendaciones generales"
            }
        
        # Contar por categoría
        categorias_encontradas = {}
        for producto in productos:
            categoria = producto.get('categoria', 'default') or 'default'
            if categoria not in categorias_encontradas:
                categorias_encontradas[categoria] = 0
            categorias_encontradas[categoria] += producto['cantidad']
        
        # Obtener categoría principal
        categoria_principal = max(categorias_encontradas, key=categorias_encontradas.get)
        
        # Obtener recomendaciones
        peliculas = RECOMENDACIONES_POR_COMIDA.get(categoria_principal, RECOMENDACIONES_POR_COMIDA["default"])
        peliculas_seleccionadas = random.sample(peliculas, min(3, len(peliculas)))
        
        return {
            "recomendaciones": peliculas_seleccionadas,
            "categoria": categoria_principal,
            "pedido_id": pedido_id,
            "mensaje": f"¡Disfruta estas películas con tu {categoria_principal}!"
        }
        
    except Exception as e:
        print(f"Error obteniendo recomendaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categorias")
async def obtener_categorias_disponibles():
    """Obtener todas las categorías de comida disponibles"""
    return {
        "categorias": list(RECOMENDACIONES_POR_COMIDA.keys()),
        "total": len(RECOMENDACIONES_POR_COMIDA)
    }