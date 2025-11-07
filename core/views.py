# core/views.py
from rest_framework import viewsets, permissions,status
from rest_framework.permissions import IsAuthenticated
from django.db.models import QuerySet
from django.db import connection
from .models import Cliente, Cartera, Pago, Prestamo, Interes, Prestamo, Cuota, Pago, PagoDetalle
from .serializers import ClienteSerializer, CarteraSerializer, PrestamoSerializer, PagoSerializer, InteresSerializer, PrestamoSerializer, CuotaSerializer, PagoSerializer
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.decorators import action, api_view, permission_classes
from django.utils import timezone
from .permissions import IsCarteraMemberOrAdmin, IsSystemAdmin, IsMemberOfCarteraOrAdmin,es_admin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .services import generar_calendario, aplicar_pago, actualizar_estado_por_mora

# Importaciones para el proxy de media seguro
import requests
from django.http import HttpResponse, Http404
from django.views.decorators.cache import cache_control
from django.conf import settings


User = get_user_model()


class InteresViewSet(viewsets.ModelViewSet):
    queryset = Interes.objects.all().order_by('nombre')
    serializer_class = InteresSerializer
@method_decorator(csrf_exempt, name='dispatch')
class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all().order_by('-created_at')
    serializer_class = ClienteSerializer
    authentication_classes = [] 
    permission_classes = [permissions.AllowAny]  # abierto mientras pruebas

class CarteraViewSet(viewsets.ModelViewSet):
    queryset = Cartera.objects.all().order_by('id')
    serializer_class   = CarteraSerializer
    authentication_classes = [] 
    permission_classes = [permissions.AllowAny]

    # def get_queryset(self) -> QuerySet:
    #     user = self.request.user
    #     qs = Cartera.objects.all().order_by('-created_at')
    #     if user.is_superuser or user.groups.filter(name='admin').exists():
    #         return qs
    #     # solo carteras donde es miembro
    #     return qs.filter(asignaciones__usuario=user).distinct()

    # create: permitido por IsSystemAdmin (via has_permission)
    # def create(self, request, *args, **kwargs):
    #     if not IsSystemAdmin().has_permission(request, self):
    #         return Response({'detail': 'Solo admin puede crear carteras.'}, status=status.HTTP_403_FORBIDDEN)
    #     return super().create(request, *args, **kwargs)

    # update/partial_update/destroy: también solo admin (en has_object_permission lo negamos a no-admin)
    # Si quieres permitir a gestores editar descripción, ajusta el permiso.

    @action(detail=True, methods=['post'], url_path='asignar', permission_classes=[permissions.AllowAny])
    def asignar_miembro(self, request, pk=None):
        cartera = self.get_object()
        ser = CarteraAsignarMiembroSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        usuario = ser.validated_data['usuario']
        rol     = ser.validated_data['rol']
        asign, created = CarteraMiembro.objects.get_or_create(cartera=cartera, usuario=usuario, defaults={'rol': rol})
        if not created:
            asign.rol = rol
            asign.save()
        return Response({'ok': True, 'miembro': {'usuario_id': usuario.id, 'rol': rol}})

    @action(detail=True, methods=['post'], url_path='quitar', permission_classes=[permissions.AllowAny])
    def quitar_miembro(self, request, pk=None):
        cartera = self.get_object()
        usuario_id = request.data.get('usuario_id')
        if not usuario_id:
            return Response({'detail': 'usuario_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        CarteraMiembro.objects.filter(cartera=cartera, usuario_id=usuario_id).delete()
        return Response({'ok': True})
    
class PrestamoViewSet(viewsets.ModelViewSet):
    queryset = Prestamo.objects.select_related('cliente','cartera','interes')
    serializer_class = PrestamoSerializer

    def list(self, request, *args, **kwargs):
        """Lista préstamos actualizando estados automáticamente"""
        from .services import actualizar_estados_cuotas, actualizar_estados_prestamos
        # Actualizar estados antes de mostrar la lista
        actualizar_estados_cuotas()
        actualizar_estados_prestamos()
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """Obtiene un préstamo específico actualizando estados"""
        from .services import actualizar_estados_cuotas, actualizar_estados_prestamos
        # Actualizar estados antes de mostrar el préstamo
        actualizar_estados_cuotas()
        actualizar_estados_prestamos()
        return super().retrieve(request, *args, **kwargs)

    def perform_create(self, serializer):
        prestamo = serializer.save()
        generar_calendario(prestamo)

    @action(detail=True, methods=['post'])
    def regenerar_calendario(self, request, pk=None):
        prestamo = self.get_object()
        generar_calendario(prestamo)
        return Response({'detail': 'Calendario regenerado'})

    @action(detail=True, methods=['post'])
    def actualizar_mora(self, request, pk=None):
        prestamo = self.get_object()
        actualizar_estado_por_mora(prestamo)
        return Response({'detail': 'Estado de mora actualizado'})

class CuotaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CuotaSerializer
    
    def list(self, request, *args, **kwargs):
        """Lista cuotas actualizando estados automáticamente"""
        from .services import actualizar_estados_cuotas
        # Actualizar estados de cuotas antes de mostrar la lista
        actualizar_estados_cuotas()
        return super().list(request, *args, **kwargs)
    
    def get_queryset(self):
        qs = Cuota.objects.select_related('prestamo')
        prestamo_id = self.request.query_params.get('prestamo')
        if prestamo_id:
            qs = qs.filter(prestamo_id=prestamo_id).order_by('numero')
        return qs

class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.select_related('prestamo')
    serializer_class = PagoSerializer

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        pago = Pago.objects.get(pk=resp.data['id'])
        aplicar_pago(pago)
        serializer = self.get_serializer(pago)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me_view(request):
    u = request.user
    return Response({
        "id": u.id,
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "email": u.email,
        # Aquí luego puedes incluir grupos/permisos si los usas
        # "groups": list(u.groups.values_list("name", flat=True)),
    })

@api_view(["GET", "POST"])
@permission_classes([permissions.AllowAny])
def actualizar_estados_view(request):
    """
    Vista para actualizar automáticamente los estados de préstamos y cuotas.
    GET: Muestra estadísticas generales de estados
    POST: Ejecuta la actualización automática de estados
    """
    try:
        from .services import actualizar_estados_prestamos, actualizar_estados_cuotas
        from .models import Prestamo, Cuota
        from datetime import date
        
        if request.method == "POST":
            # Ejecutar actualización de estados
            print("🔄 Iniciando actualización automática de estados...")
            
            # Actualizar estados de cuotas y préstamos
            cuotas_mora, cuotas_pagadas = actualizar_estados_cuotas()
            prestamos_mora, prestamos_pagados = actualizar_estados_prestamos()
            
            return Response({
                'success': True,
                'message': 'Estados actualizados correctamente',
                'fecha_actualizacion': date.today().isoformat(),
                'resultados': {
                    'cuotas': {
                        'actualizadas_a_mora': cuotas_mora,
                        'actualizadas_a_pagada': cuotas_pagadas
                    },
                    'prestamos': {
                        'actualizados_a_mora': prestamos_mora,
                        'actualizados_a_pagado': prestamos_pagados
                    },
                    'total_actualizaciones': cuotas_mora + cuotas_pagadas + prestamos_mora + prestamos_pagados
                }
            })
        else:
            # GET: Mostrar estadísticas actuales
            fecha_hoy = date.today()
            
            # Estadísticas de cuotas
            cuotas_vencidas_pendientes = Cuota.objects.filter(
                fecha_vencimiento__lt=fecha_hoy,
                estado=Cuota.Estado.PENDIENTE
            ).count()
            
            # Estadísticas de préstamos
            prestamos_con_mora = Prestamo.objects.filter(
                estado=Prestamo.Estado.PENDIENTE,
                cuotas__fecha_vencimiento__lt=fecha_hoy,
                cuotas__estado__in=[Cuota.Estado.PENDIENTE, Cuota.Estado.MORA]
            ).distinct().count()
            
            total_prestamos_activos = Prestamo.objects.filter(
                estado__in=[Prestamo.Estado.PENDIENTE, Prestamo.Estado.MORA]
            ).count()
            
            return Response({
                'fecha_consulta': fecha_hoy.isoformat(),
                'estadisticas': {
                    'cuotas_vencidas_pendientes': cuotas_vencidas_pendientes,
                    'prestamos_con_mora_potencial': prestamos_con_mora,
                    'total_prestamos_activos': total_prestamos_activos
                },
                'acciones': {
                    'actualizar_estados': 'POST a esta URL para ejecutar actualización automática',
                    'descripcion': 'Actualiza cuotas vencidas a MORA y préstamos con cuotas en mora'
                }
            })
            
    except Exception as e:
        import traceback
        return Response({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)

@api_view(["GET"])
@permission_classes([IsAuthenticated])  # Ahora requiere autenticación
def dashboard_view(request):
    """
    Endpoint para obtener métricas del dashboard por cartera del usuario autenticado:
    - Dinero disponible (total cobrado)
    - Cartera por cobrar contable  
    - Saldo contractual pendiente
    - Clientes activos
    
    Retorna métricas para cada cartera donde el usuario es miembro.
    
    Parámetros opcionales:
    - cartera_id: UUID de una cartera específica (debe ser miembro)
    """
    user = request.user
    cartera_id = request.GET.get('cartera_id')
    
    try:
        # Obtener carteras donde el usuario es miembro
        from .models import Cartera, CarteraMiembro
        carteras_usuario = Cartera.objects.filter(
            asignaciones__usuario=user
        ).select_related().prefetch_related('asignaciones')
        
        if not carteras_usuario.exists():
            return Response({
                'message': 'No tienes carteras asignadas',
                'carteras': []
            })
        
        # Si se especifica una cartera, validar que el usuario sea miembro
        if cartera_id:
            try:
                from uuid import UUID
                cartera_uuid = UUID(cartera_id)
                cartera_especifica = carteras_usuario.filter(id=cartera_uuid).first()
                if not cartera_especifica:
                    return Response({
                        'error': 'No tienes acceso a esta cartera o no existe',
                        'cartera_id': cartera_id
                    }, status=403)
                carteras_usuario = [cartera_especifica]
            except ValueError:
                return Response({
                    'error': 'cartera_id debe ser un UUID válido',
                    'cartera_id': cartera_id
                }, status=400)
        
        # Calcular métricas para cada cartera
        resultados = []
        
        for cartera in carteras_usuario:
            try:
                # Usar Django ORM para cálculos más confiables y compatibles entre BD
                from django.db.models import Sum, Count, Q, F, Case, When, DecimalField, Value
                from django.db.models.functions import Coalesce
                from decimal import Decimal
                from datetime import date
                
                # 1. Dinero disponible (total cobrado) - Compatible con PostgreSQL y SQLite
                dinero_disponible = PagoDetalle.objects.filter(
                    cuota__prestamo__cartera=cartera
                ).aggregate(
                    total=Coalesce(
                        Sum(F('capital_aplicado') + F('interes_aplicado')), 
                        Value(0, output_field=DecimalField())
                    )
                )['total']
                
                # 2. Cálculos de saldos pendientes - Optimizado para PostgreSQL
                cuotas_con_pagos = Cuota.objects.filter(
                    prestamo__cartera=cartera
                ).annotate(
                    capital_aplicado_total=Coalesce(
                        Sum('aplicaciones__capital_aplicado'), 
                        Value(0, output_field=DecimalField())
                    ),
                    interes_aplicado_total=Coalesce(
                        Sum('aplicaciones__interes_aplicado'), 
                        Value(0, output_field=DecimalField())
                    ),
                    capital_pendiente=F('capital_programado') - F('capital_aplicado_total'),
                    interes_pendiente=F('interes_programado') - F('interes_aplicado_total'),
                    esta_vencido=Case(
                        When(fecha_vencimiento__lte=date.today(), then=Value(True)),
                        default=Value(False),
                        output_field=DecimalField()
                    )
                )
                
                # Calcular totales usando agregaciones optimizadas
                saldos = cuotas_con_pagos.aggregate(
                    capital_pendiente_total=Coalesce(
                        Sum('capital_pendiente'), 
                        Value(0, output_field=DecimalField())
                    ),
                    interes_devengado_total=Coalesce(
                        Sum(Case(
                            When(fecha_vencimiento__lte=date.today(), 
                                 then='interes_pendiente'),
                            default=Value(0, output_field=DecimalField())
                        )), 
                        Value(0, output_field=DecimalField())
                    ),
                    interes_pendiente_total=Coalesce(
                        Sum('interes_pendiente'), 
                        Value(0, output_field=DecimalField())
                    )
                )
                
                capital_pendiente = saldos['capital_pendiente_total']
                interes_devengado = saldos['interes_devengado_total'] 
                interes_pendiente_total = saldos['interes_pendiente_total']
                
                # 3. Métricas finales
                cartera_por_cobrar = capital_pendiente + interes_devengado
                saldo_contractual = capital_pendiente + interes_pendiente_total
                
                # 4. Clientes activos - Compatible con ambas BD
                clientes_activos = Cliente.objects.filter(
                    prestamos__cartera=cartera,
                    activo=True
                ).distinct().count()
                
                # Obtener rol del usuario en esta cartera
                asignacion = cartera.asignaciones.filter(usuario=user).first()
                rol_usuario = asignacion.rol if asignacion else None
                
                cartera_data = {
                    'cartera': {
                        'id': str(cartera.id),
                        'nombre': cartera.nombre,
                        'descripcion': cartera.descripcion,
                        'rol_usuario': rol_usuario
                    },
                    'metricas': {
                        'dinero_disponible': float(dinero_disponible),
                        'cartera_por_cobrar_contable': float(cartera_por_cobrar),
                        'saldo_contractual_pendiente': float(saldo_contractual),
                        'clientes_activos': clientes_activos
                    }
                }
                
                resultados.append(cartera_data)
                    
            except Exception as e:
                return Response({
                    'error': 'Error procesando cartera',
                    'mensaje': str(e)
                }, status=500)
        
        # Preparar respuesta
        response_data = {
            'usuario': {
                'id': user.id,
                'username': user.username,
                'nombre_completo': f"{user.first_name} {user.last_name}".strip()
            },
            'tipo_consulta': 'cartera_especifica' if cartera_id else 'carteras_usuario',
            'total_carteras': len(resultados),
            'carteras': resultados
        }
        
        # Si es una cartera específica, simplificar la respuesta
        if cartera_id and resultados:
            cartera_data = resultados[0]
            response_data = {
                **response_data,
                'cartera_seleccionada': cartera_data['cartera'],
                'metricas': cartera_data['metricas']
            }
        
        return Response(response_data)
        
    except Exception as e:
        return Response({
            'error': 'Error interno del servidor',
            'mensaje': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_auth(request):
    """Endpoint para testear si la autenticación JWT funciona correctamente"""
    
    # Headers recibidos
    headers_info = {}
    for key, value in request.META.items():
        if key.startswith('HTTP_'):
            header_name = key[5:].replace('_', '-').title()
            if 'authorization' in header_name.lower():
                headers_info[header_name] = value[:50] + '...' if len(value) > 50 else value
            elif header_name in ['Content-Type', 'Accept', 'User-Agent', 'Origin']:
                headers_info[header_name] = value
    
    return Response({
        'authenticated': True,
        'user': request.user.username,
        'user_id': request.user.id,
        'message': 'Autenticación exitosa',
        'debug_info': {
            'headers_received': headers_info,
            'request_method': request.method,
            'request_path': request.path,
            'has_auth_header': 'HTTP_AUTHORIZATION' in request.META,
            'user_is_authenticated': request.user.is_authenticated,
            'user_is_anonymous': request.user.is_anonymous,
        }
    })


@api_view(['GET']) 
@permission_classes([permissions.AllowAny])
def debug_frontend(request):
    """Endpoint público para diagnosticar problemas del frontend"""
    
    # Headers recibidos
    headers_info = {}
    for key, value in request.META.items():
        if key.startswith('HTTP_'):
            header_name = key[5:].replace('_', '-').title()
            headers_info[header_name] = value[:100] + '...' if len(value) > 100 else value
    
    # Importar settings para ver configuración actual
    from django.conf import settings
    
    return Response({
        'message': 'Endpoint de debug - Frontend puede acceder sin autenticación',
        'timestamp': timezone.now().isoformat(),
        'headers_received': headers_info,
        'request_info': {
            'method': request.method,
            'path': request.path,
            'query_params': dict(request.GET),
            'user': str(request.user),
            'is_authenticated': request.user.is_authenticated,
        },
        'cors_config': {
            'CORS_ALLOWED_ORIGINS': getattr(settings, 'CORS_ALLOWED_ORIGINS', 'NO CONFIGURADO'),
            'CORS_ALLOW_CREDENTIALS': getattr(settings, 'CORS_ALLOW_CREDENTIALS', 'NO CONFIGURADO'),
            'DEBUG': getattr(settings, 'DEBUG', 'NO CONFIGURADO'),
        },
        'instructions': {
            'next_step': 'Intenta hacer login y luego llamar a /api/dashboard/',
            'expected_header': 'Authorization: Bearer <tu-token-jwt>',
            'test_endpoints': [
                'POST /api/token/ (login)',
                'GET /api/me/ (requiere auth)',
                'GET /api/dashboard/ (requiere auth)',
                'GET /api/test-auth/ (requiere auth)',
            ]
        }
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def debug_login(request):
    """Endpoint para diagnosticar problemas específicos de login en producción"""
    from django.contrib.auth import authenticate
    from django.conf import settings
    
    # Obtener datos del request
    try:
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        
        debug_info = {
            'timestamp': timezone.now().isoformat(),
            'request_data_received': {
                'username': username,
                'password_length': len(password) if password else 0,
                'has_username': bool(username),
                'has_password': bool(password)
            },
            'django_settings': {
                'DEBUG': settings.DEBUG,
                'DATABASE_ENGINE': settings.DATABASES['default']['ENGINE'],
                'USE_TZ': settings.USE_TZ,
                'AUTH_PASSWORD_VALIDATORS': len(settings.AUTH_PASSWORD_VALIDATORS)
            },
            'user_check': None,
            'authentication_result': None,
            'error': None
        }
        
        # Verificar si el usuario existe
        if username:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user_exists = User.objects.filter(username=username).exists()
                user_is_active = None
                if user_exists:
                    user = User.objects.get(username=username)
                    user_is_active = user.is_active
                    
                debug_info['user_check'] = {
                    'exists': user_exists,
                    'is_active': user_is_active,
                    'user_count_total': User.objects.count()
                }
            except Exception as e:
                debug_info['user_check'] = {'error': str(e)}
        
        # Intentar autenticación si tenemos credenciales
        if username and password:
            try:
                user = authenticate(username=username, password=password)
                debug_info['authentication_result'] = {
                    'success': user is not None,
                    'user_id': user.id if user else None,
                    'user_username': user.username if user else None
                }
            except Exception as e:
                debug_info['authentication_result'] = {'error': str(e)}
        
        return Response({
            'message': 'Diagnóstico de login completado',
            'debug_info': debug_info,
            'recommendations': [
                'Verifica que el usuario existe en la base de datos',
                'Confirma que la contraseña es correcta',
                'Revisa que el usuario esté activo (is_active=True)',
                'Usa este endpoint solo para debugging, no en producción real'
            ]
        })
        
    except Exception as e:
        return Response({
            'message': 'Error durante diagnóstico de login',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


@cache_control(max_age=3600)  # Cache por 1 hora
def secure_media_proxy(request, path):
    """
    Proxy seguro para servir archivos media de Cloudinary
    Solo usuarios autenticados pueden acceder a las imágenes
    """
    print(f"🔑 [PROXY] Iniciando proxy para: {path}")
    
    # Verificación manual de autenticación JWT
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework.exceptions import AuthenticationFailed
    from django.http import JsonResponse
    from urllib.parse import unquote
    
    # Decodificar la URL (espacios y caracteres especiales)
    decoded_path = unquote(path)
    print(f"🔓 [PROXY] Path decodificado: {decoded_path}")
    
    try:
        # Autenticar usuario con JWT
        jwt_auth = JWTAuthentication()
        auth_result = jwt_auth.authenticate(request)
        
        if not auth_result:
            print(f"❌ [PROXY] No se encontró token de autenticación")
            print(f"❌ [PROXY] Headers disponibles: {list(request.headers.keys())}")
            auth_header = request.headers.get('Authorization')
            print(f"❌ [PROXY] Authorization header: {auth_header}")
            return JsonResponse({
                'error': 'Token de autenticación requerido',
                'details': 'No se encontró el header Authorization con un token JWT válido'
            }, status=401)
        
        user, token = auth_result
        if not user.is_authenticated:
            print(f"❌ [PROXY] Usuario no autenticado: {user}")
            return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
        
        print(f"✅ [PROXY] Usuario autenticado: {user.username}")
            
        # Servir archivo si está autenticado
        if settings.USE_CLOUDINARY:
            # Construir URL de Cloudinary
            cloud_name = settings.CLOUDINARY_STORAGE.get('CLOUD_NAME')
            if not cloud_name:
                print(f"❌ [PROXY] Configuración de Cloudinary no encontrada")
                raise Http404("Configuración de Cloudinary no encontrada")
            
            # Usar path decodificado para construir URL de Cloudinary
            cloudinary_url = f"https://res.cloudinary.com/{cloud_name}/image/upload/v1/{decoded_path}"
            
            print(f"✅ [PROXY] Accediendo a archivo: {decoded_path}")
            print(f"🔗 [PROXY] URL de Cloudinary: {cloudinary_url}")
            
            # Hacer request a Cloudinary con timeout
            response = requests.get(cloudinary_url, timeout=10)
            
            print(f"📊 [PROXY] Status Cloudinary: {response.status_code}")
            if response.status_code != 200:
                print(f"❌ [PROXY] Error en Cloudinary: {response.status_code}")
                print(f"❌ [PROXY] Respuesta: {response.text[:200]}")
            else:
                print(f"✅ [PROXY] Imagen encontrada, sirviendo archivo")
            
            if response.status_code == 200:
                # Determinar content type basado en la extensión
                content_type = response.headers.get('content-type', 'image/jpeg')
                
                # Crear respuesta HTTP con la imagen
                http_response = HttpResponse(response.content, content_type=content_type)
                http_response['Content-Length'] = len(response.content)
                http_response['Cache-Control'] = 'private, max-age=3600'
                
                # Headers adicionales de seguridad
                http_response['X-Content-Type-Options'] = 'nosniff'
                http_response['X-Frame-Options'] = 'DENY'
                
                return http_response
            else:
                print(f"Error obteniendo imagen de Cloudinary: {response.status_code}")
                raise Http404("Archivo no encontrado en Cloudinary")
        else:
            # En desarrollo local, servir archivo directamente
            from django.views.static import serve
            import os
            
            # Verificar que el archivo existe usando path decodificado
            file_path = os.path.join(settings.MEDIA_ROOT, decoded_path)
            if not os.path.exists(file_path):
                print(f"❌ Archivo no encontrado en: {file_path}")
                raise Http404("Archivo no encontrado")
            
            print(f"✅ Sirviendo archivo local: {file_path}")
            return serve(request, decoded_path, document_root=settings.MEDIA_ROOT)
            
    except AuthenticationFailed as e:
        print(f"❌ [PROXY] Error de autenticación: {e}")
        return JsonResponse({
            'error': 'Token inválido o expirado',
            'details': str(e)
        }, status=401)
    except requests.RequestException as e:
        print(f"❌ [PROXY] Error de red sirviendo media: {e}")
        return JsonResponse({
            'error': 'Error al acceder al archivo',
            'details': 'Error de conexión con Cloudinary'
        }, status=503)
    except Exception as e:
        print(f"❌ [PROXY] Error general sirviendo media: {e}")
        import traceback
        print(f"❌ [PROXY] Traceback: {traceback.format_exc()}")
        return JsonResponse({
            'error': 'Error interno del servidor',
            'details': str(e)
        }, status=500)
