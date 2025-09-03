# core/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import CarteraMiembro, Prestamo, Pago

def es_admin(user):
    return user.is_superuser or user.groups.filter(name='admin').exists()

class IsSystemAdmin(BasePermission):
    """
    Permite solo a superusers o usuarios en grupo 'admin' (ajústalo a tu gusto).
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        # si usas grupos:
        return user.groups.filter(name='admin').exists()

class IsCarteraMemberOrAdmin(BasePermission):
    """
    - GET/LIST de carteras: miembro o admin
    - Otros métodos (PUT/PATCH/DELETE): sólo admin (crear también solo admin).
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        # Crear: solo admin
        if request.method not in SAFE_METHODS and view.action == 'create':
            return IsSystemAdmin().has_permission(request, view)
        return True

    def has_object_permission(self, request, view, obj):
        # Admin siempre puede
        if IsSystemAdmin().has_permission(request, view):
            return True
        if request.method in SAFE_METHODS:
            # Ver objeto: debe ser miembro
            return obj.asignaciones.filter(usuario=request.user).exists()
        # Modificar/eliminar: solo admin
        return False

class IsMemberOfCarteraOrAdmin(BasePermission):
    """
    Aplica a Prestamo y Pago:
    - Admin => acceso total
    - No admin => debe ser miembro de la cartera del préstamo
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if es_admin(request.user):
            return True

        # obj puede ser Prestamo o Pago
        if isinstance(obj, Prestamo):
            cartera = obj.cartera
        elif isinstance(obj, Pago):
            cartera = obj.prestamo.cartera
        else:
            return False

        return CarteraMiembro.objects.filter(cartera=cartera, usuario=request.user).exists()