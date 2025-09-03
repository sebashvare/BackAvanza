# core/views.py
from rest_framework import viewsets, permissions,status
from django.db.models import QuerySet
from .models import Cliente, Cartera, Pago, Prestamo
from .serializers import ClienteSerializer, CarteraSerializer, PrestamoSerializer, PagoSerializer
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.decorators import action
from .permissions import IsCarteraMemberOrAdmin, IsSystemAdmin, IsMemberOfCarteraOrAdmin,es_admin


User = get_user_model()

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all().order_by('-created_at')
    serializer_class = ClienteSerializer
    permission_classes = [permissions.AllowAny]  # abierto mientras pruebas

class CarteraViewSet(viewsets.ModelViewSet):
    serializer_class   = CarteraSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self) -> QuerySet:
        user = self.request.user
        qs = Cartera.objects.all().order_by('-created_at')
        if user.is_superuser or user.groups.filter(name='admin').exists():
            return qs
        # solo carteras donde es miembro
        return qs.filter(asignaciones__usuario=user).distinct()

    # create: permitido por IsSystemAdmin (via has_permission)
    def create(self, request, *args, **kwargs):
        if not IsSystemAdmin().has_permission(request, self):
            return Response({'detail': 'Solo admin puede crear carteras.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

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
    serializer_class   = PrestamoSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self) -> QuerySet:
        user = self.request.user
        qs = Prestamo.objects.select_related('cliente','cartera').order_by('-created_at')
        if es_admin(user):
            return qs
        # solo de carteras donde el user es miembro
        return qs.filter(cartera__asignaciones__usuario=user).distinct()

class PagoViewSet(viewsets.ModelViewSet):
    serializer_class   = PagoSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self) -> QuerySet:
        user = self.request.user
        qs = Pago.objects.select_related('prestamo','prestamo__cartera','prestamo__cliente').order_by('-created_at')
        if es_admin(user):
            return qs
        return qs.filter(prestamo__cartera__asignaciones__usuario=user).distinct()
