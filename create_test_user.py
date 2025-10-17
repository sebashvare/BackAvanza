#!/usr/bin/env python3
"""
Script para crear un usuario de prueba para las pruebas del sistema
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User

def create_test_user():
    """Crear usuario de prueba"""
    username = "Sebastian"
    password = "Sebas_123"
    email = "sebastian@test.com"
    
    try:
        # Verificar si el usuario ya existe
        if User.objects.filter(username=username).exists():
            print(f"✅ Usuario '{username}' ya existe")
            user = User.objects.get(username=username)
            # Actualizar contraseña por si acaso
            user.set_password(password)
            user.save()
            print(f"🔄 Contraseña actualizada para '{username}'")
        else:
            # Crear nuevo usuario
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            print(f"✅ Usuario '{username}' creado exitosamente")
            
        # Hacer al usuario admin si no lo es
        if not user.is_staff:
            user.is_staff = True
            user.is_superuser = True
            user.save()
            print(f"🔑 '{username}' ahora es administrador")
            
        return True
        
    except Exception as e:
        print(f"❌ Error creando usuario: {e}")
        return False

def list_existing_users():
    """Listar usuarios existentes"""
    print("\n📋 USUARIOS EXISTENTES:")
    users = User.objects.all()
    
    if users:
        for user in users:
            admin_status = "👑 Admin" if user.is_superuser else "👤 Usuario"
            print(f"  - {user.username} ({user.email}) - {admin_status}")
    else:
        print("  No hay usuarios en el sistema")
        
    return len(users)

if __name__ == "__main__":
    print("🔧 CONFIGURACIÓN DE USUARIOS PARA PRUEBAS")
    print("="*50)
    
    # Listar usuarios existentes
    user_count = list_existing_users()
    
    # Crear usuario de prueba
    print(f"\n🆕 CREANDO USUARIO DE PRUEBA:")
    success = create_test_user()
    
    if success:
        print(f"\n✅ ¡Configuración completada!")
        print(f"   Puedes usar: Sebastian / Sebas_123")
        print(f"   Admin en: http://127.0.0.1:8000/admin/")
    else:
        print(f"\n❌ Error en la configuración")