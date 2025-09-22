#!/usr/bin/env python
"""
Script de inicio rápido para desarrollo.
"""

import os
import sys
import subprocess
import django
from pathlib import Path

def run_command(command, description):
    """Ejecutar comando y mostrar resultado."""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completado")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}:")
        print(e.stderr)
        return False

def main():
    """Función principal."""
    print("🚀 Iniciando Material Management API...")
    
    # Verificar si estamos en el directorio correcto
    if not Path("manage.py").exists():
        print("❌ Error: No se encontró manage.py. Ejecuta desde el directorio raíz del proyecto.")
        sys.exit(1)
    
    # Verificar si existe el entorno virtual
    if not Path("env").exists():
        print("❌ Error: No se encontró el entorno virtual 'env'.")
        print("Crea el entorno virtual con: python -m venv env")
        sys.exit(1)
    
    # Verificar si existe el archivo .env
    if not Path(".env").exists():
        print("⚠️  Advertencia: No se encontró archivo .env")
        print("Copia env.example a .env y configura las variables necesarias")
        if Path("env.example").exists():
            print("Ejecuta: cp env.example .env")
    
    # Comandos a ejecutar
    commands = [
        ("python manage.py makemigrations", "Creando migraciones"),
        ("python manage.py migrate", "Aplicando migraciones"),
        ("python manage.py init_data --create-superuser --create-platform-specs", "Inicializando datos"),
    ]
    
    # Ejecutar comandos
    for command, description in commands:
        if not run_command(command, description):
            print(f"❌ Falló: {description}")
            sys.exit(1)
    
    print("\n🎉 ¡Configuración completada!")
    print("\n📋 Próximos pasos:")
    print("1. Configura tu archivo .env con las variables necesarias")
    print("2. Ejecuta: python manage.py runserver")
    print("3. Accede a: http://localhost:8000/api/docs/")
    print("4. Login con: admin/admin123")
    
    # Preguntar si quiere ejecutar el servidor
    response = input("\n¿Quieres ejecutar el servidor ahora? (y/n): ").lower().strip()
    if response in ['y', 'yes', 'sí', 'si']:
        print("\n🚀 Iniciando servidor...")
        os.system("python manage.py runserver")

if __name__ == "__main__":
    main()
