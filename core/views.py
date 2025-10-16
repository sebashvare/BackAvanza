# core/views.py
from rest_framework import viewsets, permissions,status
from django.db.models import QuerySet
from django.db import connection
from .models import Cliente, Cartera, Pago, Prestamo, Interes, Prestamo, Cuota, Pago
from .serializers import ClienteSerializer, CarteraSerializer, PrestamoSerializer, PagoSerializer, InteresSerializer, PrestamoSerializer, CuotaSerializer, PagoSerializer
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.decorators import action, api_view, permission_classes
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
@permission_classes([permissions.AllowAny])  # Ajusta según tus necesidades de permisos
def dashboard_view(request):
    """
    Endpoint para obtener métricas del dashboard:
    - Dinero disponible (total cobrado)
    - Cartera por cobrar contable
    - Saldo contractual pendiente
    - Clientes activos
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            WITH
            pagos AS (
              SELECT 
                SUM(COALESCE(d.capital_aplicado,0) + COALESCE(d.interes_aplicado,0)) AS cobrado_total
              FROM pagos_detalle d
            ),
            cuotas_base AS (
              SELECT
                c.id,
                c.capital_programado,
                c.interes_programado,
                c.fecha_vencimiento,
                COALESCE(pd.cap_apl, 0) AS cap_apl,
                COALESCE(pd.int_apl, 0) AS int_apl
              FROM cuotas c
              LEFT JOIN (
                SELECT 
                  cuota_id,
                  SUM(COALESCE(capital_aplicado,0)) AS cap_apl,
                  SUM(COALESCE(interes_aplicado,0)) AS int_apl
                FROM pagos_detalle
                GROUP BY cuota_id
              ) pd ON pd.cuota_id = c.id
            ),
            saldos AS (
              SELECT
                SUM(capital_programado - cap_apl) AS saldo_capital_pendiente,
                SUM(CASE WHEN DATE(fecha_vencimiento) <= CURRENT_DATE
                         THEN interes_programado - int_apl
                         ELSE 0 END) AS interes_devengado_pendiente,
                SUM((capital_programado - cap_apl) + (interes_programado - int_apl)) AS saldo_contractual_pendiente
              FROM cuotas_base
            )
            SELECT
              COALESCE((SELECT cobrado_total FROM pagos), 0)                                           AS dinero_disponible,
              COALESCE(saldo_capital_pendiente, 0) + COALESCE(interes_devengado_pendiente, 0)         AS cartera_por_cobrar_contable,
              COALESCE(saldo_contractual_pendiente, 0)                                                AS saldo_contractual_pendiente,
              (SELECT COUNT(*) FROM clientes WHERE activo IS TRUE)                                     AS clientes_activos
            FROM saldos;
        """)
        
        row = cursor.fetchone()
        
        if row:
            data = {
                'dinero_disponible': float(row[0]) if row[0] else 0.0,
                'cartera_por_cobrar_contable': float(row[1]) if row[1] else 0.0,
                'saldo_contractual_pendiente': float(row[2]) if row[2] else 0.0,
                'clientes_activos': int(row[3]) if row[3] else 0
            }
        else:
            # Valores por defecto si no hay datos
            data = {
                'dinero_disponible': 0.0,
                'cartera_por_cobrar_contable': 0.0,
                'saldo_contractual_pendiente': 0.0,
                'clientes_activos': 0
            }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@cache_control(max_age=3600)  # Cache por 1 hora
def secure_media_proxy(request, path):
    """
    Proxy seguro para servir archivos media de Cloudinary
    Solo usuarios autenticados pueden acceder a las imágenes
    """
    try:
        if settings.USE_CLOUDINARY:
            # Construir URL de Cloudinary
            cloud_name = settings.CLOUDINARY_STORAGE.get('CLOUD_NAME')
            if not cloud_name:
                raise Http404("Configuración de Cloudinary no encontrada")
            
            cloudinary_url = f"https://res.cloudinary.com/{cloud_name}/image/upload/v1/{path}"
            
            # Hacer request a Cloudinary con timeout
            response = requests.get(cloudinary_url, timeout=10)
            
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
            
            # Verificar que el archivo existe
            file_path = os.path.join(settings.MEDIA_ROOT, path)
            if not os.path.exists(file_path):
                raise Http404("Archivo no encontrado")
            
            return serve(request, path, document_root=settings.MEDIA_ROOT)
            
    except requests.RequestException as e:
        print(f"Error de red sirviendo media: {e}")
        raise Http404("Error al acceder al archivo")
    except Exception as e:
        print(f"Error general sirviendo media: {e}")
        raise Http404("Error al acceder al archivo")
