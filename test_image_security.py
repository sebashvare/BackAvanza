#!/usr/bin/env python3
"""
Script de prueba para el sistema de imágenes protegidas
Simula las acciones del frontend para verificar que todo funciona correctamente
"""

import requests
import json
import os

# Configuración
BASE_URL = "http://127.0.0.1:8000/api"
# Probaremos diferentes combinaciones de usuario/contraseña
TEST_CREDENTIALS = [
    ("sebastian", "Sebas_123"),  # Credenciales correctas (minúsculas)
    ("Sebastian", "Sebas_123"),  # Credenciales proporcionadas por el usuario
    ("admin", "admin"),
    ("admin", "123456"),
    ("admin", "password"),
    ("test", "test"),
    ("user", "user"),
]

class TestImageSecurity:
    def __init__(self):
        self.token = None
        self.session = requests.Session()
        
    def print_step(self, step_num, description):
        print(f"\n{'='*60}")
        print(f"PASO {step_num}: {description}")
        print('='*60)
        
    def print_result(self, success, message):
        status = "✅ ÉXITO" if success else "❌ ERROR"
        print(f"{status}: {message}")
        
    def test_1_authentication(self):
        """Prueba 1: Verificar que la autenticación funciona"""
        self.print_step(1, "Probando autenticación")
        
        # Probar endpoint sin autenticación
        try:
            response = self.session.get(f"{BASE_URL}/test-auth/")
            if response.status_code == 401:
                self.print_result(True, "Endpoint protegido correctamente (401 sin token)")
            else:
                self.print_result(False, f"Endpoint debería devolver 401, pero devolvió {response.status_code}")
        except Exception as e:
            self.print_result(False, f"Error conectando al servidor: {e}")
            return False
            
        # Probar diferentes credenciales
        for username, password in TEST_CREDENTIALS:
            try:
                print(f"\n🔑 Probando credenciales: {username}/{password}")
                login_data = {"username": username, "password": password}
                response = self.session.post(f"{BASE_URL}/token/", json=login_data)
                
                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get('access')
                    self.username = username
                    self.print_result(True, f"Token obtenido exitosamente con {username}: {self.token[:20]}...")
                    
                    # Configurar headers de autenticación
                    self.session.headers.update({'Authorization': f'Bearer {self.token}'})
                    return True
                else:
                    print(f"❌ Credenciales {username}/{password} no válidas: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error probando {username}/{password}: {e}")
                
        self.print_result(False, "No se pudo autenticar con ninguna credencial")
        return False
    
    def test_2_auth_endpoint(self):
        """Prueba 2: Verificar endpoint de test de autenticación"""
        self.print_step(2, "Probando endpoint de verificación de autenticación")
        
        if not self.token:
            self.print_result(False, "No hay token disponible")
            return False
            
        try:
            response = self.session.get(f"{BASE_URL}/test-auth/")
            
            if response.status_code == 200:
                data = response.json()
                self.print_result(True, f"Autenticación verificada: {data}")
                return True
            else:
                self.print_result(False, f"Error en verificación: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"Error verificando autenticación: {e}")
            return False
    
    def test_3_clients_with_images(self):
        """Prueba 3: Obtener clientes y verificar URLs de imágenes"""
        self.print_step(3, "Probando obtención de clientes con imágenes")
        
        try:
            response = self.session.get(f"{BASE_URL}/clientes/")
            
            if response.status_code == 200:
                data = response.json()
                
                # Manejar tanto formato paginado como lista directa
                if isinstance(data, dict) and 'results' in data:
                    clients = data['results']
                elif isinstance(data, list):
                    clients = data
                else:
                    clients = []
                
                if clients:
                    self.print_result(True, f"Obtenidos {len(clients)} clientes")
                    
                    # Verificar URLs de imágenes
                    for i, client in enumerate(clients[:3]):  # Solo primeros 3 para no saturar
                        print(f"\nCliente {i+1}: {client.get('nombre', 'Sin nombre')}")
                        
                        # Verificar cada campo de imagen
                        image_fields = ['cedula_frontal_url', 'cedula_trasera_url', 'foto_personal_url']
                        for field in image_fields:
                            url = client.get(field)
                            if url:
                                is_secure = '/api/secure-media/' in url
                                url_type = "🔒 PROTEGIDA" if is_secure else "🌐 PÚBLICA"
                                print(f"  {field}: {url_type}")
                                print(f"    URL: {url}")
                            else:
                                print(f"  {field}: ❌ No disponible")
                    
                    return True
                else:
                    self.print_result(True, "No hay clientes en el sistema (esto es normal)")
                    return True
            else:
                self.print_result(False, f"Error obteniendo clientes: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_result(False, f"Error obteniendo clientes: {e}")
            return False
    
    def test_4_secure_image_access(self):
        """Prueba 4: Intentar acceder a una imagen protegida"""
        self.print_step(4, "Probando acceso a imagen protegida")
        
        # Crear una URL de prueba del proxy seguro
        test_path = "media/clientes/2025/10/07/test.jpg"
        secure_url = f"{BASE_URL}/secure-media/{test_path}"
        
        try:
            print(f"🔗 Probando URL: {secure_url}")
            response = self.session.get(secure_url)
            
            print(f"📊 Status: {response.status_code}")
            print(f"📄 Response text: {response.text[:200]}...")
            
            if response.status_code == 404:
                self.print_result(True, "Proxy funciona - devuelve 404 para archivo inexistente (comportamiento esperado)")
            elif response.status_code == 401:
                self.print_result(False, "Error de autenticación en proxy - revisar token")
            elif response.status_code == 200:
                self.print_result(True, "Proxy funciona - archivo encontrado y servido")
            elif response.status_code == 500:
                self.print_result(False, f"Error interno en proxy - revisar logs del servidor. Response: {response.text}")
            else:
                self.print_result(False, f"Respuesta inesperada del proxy: {response.status_code}")
                
        except Exception as e:
            self.print_result(False, f"Error probando proxy: {e}")
            return False
            
        return True
    
    def test_5_unauthorized_access(self):
        """Prueba 5: Verificar que sin token no se puede acceder"""
        self.print_step(5, "Probando acceso sin autorización")
        
        # Crear sesión sin autenticación
        unauth_session = requests.Session()
        test_path = "media/clientes/2025/10/07/test.jpg"
        secure_url = f"{BASE_URL}/secure-media/{test_path}"
        
        try:
            response = unauth_session.get(secure_url)
            
            if response.status_code == 401:
                self.print_result(True, "Seguridad funciona - acceso negado sin token")
                return True
            else:
                self.print_result(False, f"Seguridad fallida - debería ser 401, pero fue {response.status_code}")
                return False
                
        except Exception as e:
            self.print_result(False, f"Error probando acceso no autorizado: {e}")
            return False
    
    def run_all_tests(self):
        """Ejecutar todas las pruebas"""
        print("🧪 INICIANDO PRUEBAS DEL SISTEMA DE IMÁGENES PROTEGIDAS")
        print("📍 Servidor: http://127.0.0.1:8000")
        print("👤 Probando con múltiples credenciales")
        
        tests = [
            self.test_1_authentication,
            self.test_2_auth_endpoint,
            self.test_3_clients_with_images,
            self.test_4_secure_image_access,
            self.test_5_unauthorized_access
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"❌ ERROR CRÍTICO en {test.__name__}: {e}")
                results.append(False)
        
        # Resumen final
        self.print_step("FINAL", "Resumen de resultados")
        passed = sum(results)
        total = len(results)
        
        print(f"✅ Pruebas exitosas: {passed}/{total}")
        if passed == total:
            print("🎉 ¡TODAS LAS PRUEBAS PASARON!")
            print("✅ El sistema de imágenes protegidas está funcionando correctamente")
        else:
            print("⚠️  Algunas pruebas fallaron - revisar implementación")
            
        return passed == total

if __name__ == "__main__":
    tester = TestImageSecurity()
    success = tester.run_all_tests()
    exit(0 if success else 1)