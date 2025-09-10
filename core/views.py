# core/views.py
from rest_framework import viewsets, permissions,status
from django.db.models import QuerySet
from .models import Cliente, Cartera, Pago, Prestamo, Interes, Prestamo, Cuota, Pago
from .serializers import ClienteSerializer, CarteraSerializer, PrestamoSerializer, PagoSerializer, InteresSerializer, PrestamoSerializer, CuotaSerializer, PagoSerializer
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.decorators import action
from .permissions import IsCarteraMemberOrAdmin, IsSystemAdmin, IsMemberOfCarteraOrAdmin,es_admin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .services import generar_calendario, aplicar_pago, actualizar_estado_por_mora


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

