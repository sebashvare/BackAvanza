#!/usr/bin/env python3
"""
Script simple para debuggear la autenticación
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def test_login():
    """Probar login con diferentes variaciones"""
    
    # Diferentes variaciones de credenciales
    credentials_to_try = [
        ("sebastian", "Sebas_123"),
        ]
    
    print("🔍 DEBUGGEANDO AUTENTICACIÓN")
    print("="*40)
    
    for username, password in credentials_to_try:
        print(f"\n🔑 Probando: {username} / {password}")
        
        try:
            login_data = {"username": username, "password": password}
            print(f"📤 Enviando: {json.dumps(login_data)}")
            
            response = requests.post(f"{BASE_URL}/token/", json=login_data)
            print(f"📊 Status: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('access')
                print(f"✅ ¡ÉXITO! Token: {token[:30]}...")
                return token
            else:
                print(f"❌ Falló")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n❌ No se pudo autenticar con ninguna variación")
    return None

def test_token_endpoint():
    """Verificar si el endpoint de token funciona"""
    print(f"\n🔍 Verificando endpoint de token...")
    
    try:
        response = requests.get(f"{BASE_URL}/token/")
        print(f"📊 GET /token/ Status: {response.status_code}")
        print(f"📄 Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_with_admin_panel():
    """Sugerir verificación en panel admin"""
    print(f"\n💡 SUGERENCIAS:")
    print(f"1. Abrir http://127.0.0.1:8000/admin/")
    print(f"2. Verificar que el usuario 'Sebastian' existe")
    print(f"3. Verificar que tiene is_active=True")
    print(f"4. Intentar cambiar la contraseña si es necesario")

if __name__ == "__main__":
    token = test_login()
    test_token_endpoint()
    test_with_admin_panel()
    
    if token:
        print(f"\n✅ ¡Autenticación exitosa!")
    else:
        print(f"\n❌ Verificar credenciales en el admin panel")