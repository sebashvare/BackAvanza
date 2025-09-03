# core/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Cartera, CarteraMiembro, Cliente

User = get_user_model()

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'identificacion', 'email', 'telefono', 'created_at')
    search_fields = ('nombre', 'identificacion', 'email')
    list_filter   = ('created_at',)
    readonly_fields = ('id', 'created_at')

class CarteraMiembroInline(admin.TabularInline):
    model = CarteraMiembro
    extra = 0
    autocomplete_fields = ('usuario',)   # útil si activas search_fields en UserAdmin
    fields = ('usuario', 'rol', 'creado')
    readonly_fields = ('creado',)

@admin.register(Cartera)
class CarteraAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'descripcion', 'created_at')
    search_fields = ('nombre', 'descripcion')
    list_filter   = ('created_at',)
    readonly_fields = ('id', 'created_at')
    inlines = [CarteraMiembroInline]

    # Solo admins pueden añadir/eliminar (opcional):
    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name='admin').exists()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name='admin').exists()

    def has_change_permission(self, request, obj=None):
        # permitir ver/editar solo a admins (o ajusta si quieres permitir a gestores)
        return request.user.is_superuser or request.user.groups.filter(name='admin').exists()
    
@admin.register(CarteraMiembro)
class CarteraMiembroAdmin(admin.ModelAdmin):
    list_display  = ('cartera', 'usuario', 'rol', 'creado')
    list_filter   = ('rol', 'cartera')
    search_fields = ('cartera__nombre', 'usuario__email', 'usuario__username')
    autocomplete_fields = ('cartera', 'usuario')
    readonly_fields = ('id', 'creado')

    def has_module_permission(self, request):
        # opcional: solo admins ven este módulo
        return request.user.is_superuser or request.user.groups.filter(name='admin').exists()

