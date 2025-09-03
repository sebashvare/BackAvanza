# core/models.py
import uuid
from django.db import models
from django.conf import settings


# core/models.py
class Cliente(models.Model):
    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre             = models.CharField(max_length=255)
    identificacion     = models.CharField(max_length=128, unique=True)
    telefono           = models.CharField(max_length=64, blank=True, default='')
    direccion          = models.CharField(max_length=255, blank=True, default='')
    direccion_laboral  = models.CharField(max_length=255, blank=True, default='')
    email              = models.EmailField(null=True, blank=True, unique=True)
    red_social         = models.CharField(max_length=255, blank=True, default='')

    foto_cliente       = models.ImageField(upload_to='clientes/%Y/%m/%d', null=True, blank=True)
    foto_dni_1         = models.ImageField(upload_to='clientes/%Y/%m/%d', null=True, blank=True)
    foto_dni_2         = models.ImageField(upload_to='clientes/%Y/%m/%d', null=True, blank=True)

    # Datos del garante embebidos (siguen igual)
    garante_identificacion = models.CharField(max_length=128, blank=True, default='')
    garante_nombre         = models.CharField(max_length=255, blank=True, default='')
    garante_apellido       = models.CharField(max_length=255, blank=True, default='')
    garante_direccion      = models.CharField(max_length=255, blank=True, default='')
    garante_telefono       = models.CharField(max_length=64,  blank=True, default='')

    activo       = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clientes'
        indexes = [
            models.Index(fields=['identificacion'], name='idx_clientes_identificacion'),
            models.Index(fields=['email'], name='idx_clientes_email'),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.identificacion})'
    
    def save(self, *args, **kwargs):
        self.activo = True
        super().save(*args, **kwargs)
"""
Modelo: Cartera
Requisitos:
- nombre: El nombre de la cartera (string, requerido)
- descripcion: Una descripción de la cartera (string, opcional)
- propietario: El usuario que es propietario de la cartera (usuario, requerido)
"""

class Cartera(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre      = models.CharField(max_length=255, unique=True)
    descripcion = models.TextField(blank=True, default='')
    miembros    = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='CarteraMiembro',
        related_name='carteras_miembro'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'carteras'
        indexes = [models.Index(fields=['nombre'], name='idx_carteras_nombre')]

    def __str__(self):
        return self.nombre
    
class CarteraMiembro(models.Model):
    class RolEnCartera(models.TextChoices):
        GESTOR   = 'gestor', 'Gestor'
        OPERADOR = 'operador', 'Operador'

    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cartera  = models.ForeignKey(Cartera, on_delete=models.CASCADE, related_name='asignaciones')
    usuario  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='asignaciones_cartera')
    rol      = models.CharField(max_length=16, choices=RolEnCartera.choices, default=RolEnCartera.GESTOR)
    creado   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cartera_miembros'
        unique_together = ('cartera', 'usuario')  # un usuario solo una vez por cartera
        indexes = [
            models.Index(fields=['cartera', 'usuario'], name='idx_cartera_usuario'),
        ]

    def __str__(self):
        return f'{self.usuario} → {self.cartera} ({self.rol})'
    
class Prestamo(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        APROBADO  = 'aprobado',  'Aprobado'
        ACTIVO    = 'activo',    'Activo'
        MORA      = 'mora',      'Mora'
        CANCELADO = 'cancelado', 'Cancelado'
        PAGADO    = 'pagado',    'Pagado'

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente          = models.ForeignKey(Cliente, on_delete=models.RESTRICT, related_name='prestamos')
    cartera          = models.ForeignKey(Cartera, on_delete=models.CASCADE, related_name='prestamos')
    monto            = models.DecimalField(max_digits=12, decimal_places=2)
    interes_mensual  = models.DecimalField(max_digits=6, decimal_places=3)
    plazo_meses      = models.PositiveIntegerField()
    fecha_desembolso = models.DateField(auto_now_add=True)
    estado           = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prestamos'
        indexes = [
            models.Index(fields=['cartera'],       name='idx_prestamos_cartera'),
            models.Index(fields=['cliente'],       name='idx_prestamos_cliente'),
            models.Index(fields=['estado'],        name='idx_prestamos_estado'),
            models.Index(fields=['created_at'],    name='idx_prestamos_created'),
        ]

    def __str__(self):
        return f'{self.cliente} – {self.monto} ({self.estado})'

class Pago(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prestamo       = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='pagos')
    fecha_pago     = models.DateField(auto_now_add=True)
    monto          = models.DecimalField(max_digits=12, decimal_places=2)

    capital_pagado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    interes_pagado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mora_pagada    = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    metodo_pago    = models.CharField(max_length=50, blank=True, default='')
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pagos'
        indexes = [
            models.Index(fields=['prestamo', 'fecha_pago'], name='idx_pagos_prestamo_fecha'),
        ]

    def __str__(self):
        return f'Pago {self.monto} a {self.prestamo_id}'