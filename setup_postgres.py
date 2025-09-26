#!/usr/bin/env python
"""
Script para configurar PostgreSQL en desarrollo local
Ejecuta: python setup_postgres.py
"""

import os
import sys
from pathlib import Path

def create_env_file():
    """Crear archivo .env si no existe"""
    env_file = Path('.env')
    if env_file.exists():
        print("✅ Archivo .env ya existe")
        return
    
    env_example = Path('.env.example')
    if not env_example.exists():
        print("❌ No se encontró .env.example")
        return
    
    # Copiar .env.example a .env
    with open(env_example, 'r') as f:
        content = f.read()
    
    with open(env_file, 'w') as f:
        f.write(content)
    
    print("✅ Archivo .env creado desde .env.example")
    print("📝 Edita el archivo .env con tus credenciales de PostgreSQL")

def install_requirements():
    """Instalar dependencias"""
    print("📦 Instalando dependencias...")
    os.system("pip install -r requirements.txt")

def create_database_commands():
    """Mostrar comandos para crear la base de datos"""
    print("\n" + "="*50)
    print("🐘 CONFIGURACIÓN DE POSTGRESQL")
    print("="*50)
    print("\n1. Asegúrate de tener PostgreSQL instalado y ejecutándose")
    print("\n2. Crear la base de datos (ejecuta en psql o pgAdmin):")
    print("   CREATE DATABASE priscila_db;")
    print("   CREATE USER postgres WITH PASSWORD 'tu_password';")
    print("   GRANT ALL PRIVILEGES ON DATABASE priscila_db TO postgres;")
    
    print("\n3. Configurar variables de entorno en .env:")
    print("   USE_POSTGRESQL_LOCAL=true")
    print("   DB_NAME=priscila_db")
    print("   DB_USER=postgres")
    print("   DB_PASSWORD=tu_password_real")
    print("   DB_HOST=localhost")
    print("   DB_PORT=5432")
    
    print("\n4. Ejecutar migraciones:")
    print("   python manage.py makemigrations")
    print("   python manage.py migrate")
    
    print("\n5. Probar la conexión:")
    print("   python manage.py dbshell")
    
    print("\n6. Para probar el endpoint del dashboard:")
    print("   python manage.py runserver")
    print("   Visita: http://localhost:8000/api/dashboard/")
    
    print("\n" + "="*50)

def main():
    print("🚀 CONFIGURADOR DE POSTGRESQL PARA PRISCILA")
    print("="*50)
    
    # Instalar dependencias
    install_requirements()
    
    # Crear archivo .env
    create_env_file()
    
    # Mostrar instrucciones
    create_database_commands()

if __name__ == "__main__":
    main()