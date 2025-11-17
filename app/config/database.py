from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
from dotenv import load_dotenv
import random  
import time

# Cargar variables de entorno
load_dotenv()

app = FastAPI(
    title="Reelish Database API",
    description="API de Base de Datos para Restaurant App",
    version="1.0.0"
)

# ============= CORS =============
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= CONFIGURACIÓN BD =============
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USERNAME', 'root'),
    'password': os.getenv('DB_PASSWORD', '1234'),
    'database': os.getenv('DB_DATABASE', 'restaurant_app')
}

def get_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f" Error de conexión: {e}")
        raise HTTPException(status_code=500, detail=f"Error de conexión: {str(e)}")

def execute_query(query: str, params: tuple = None, fetch: bool = True):
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        if fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = {'affected_rows': cursor.rowcount, 'last_id': cursor.lastrowid}
        
        cursor.close()
        conn.close()
        return result
    except Error as e:
        print(f"Error en query: {e}")
        raise HTTPException(status_code=500, detail=f"Error en query: {str(e)}")
