# core/models.py
import uuid
from datetime import date
from django.db import models
from django.conf import settings
from decimal import Decimal


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
class Interes(models.Model):
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre  = models.CharField(max_length=128, unique=True)
    # Porcentaje plano sobre el monto del préstamo: 0.20 = 20%
    tasa_decimal = models.DecimalField(max_digits=8, decimal_places=6, help_text="0.20 = 20%")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'intereses'
        indexes = [models.Index(fields=['nombre'], name='idx_intereses_nombre')]

    def __str__(self):
        return f'{self.nombre} ({self.tasa_decimal})'
class Prestamo(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        MORA      = 'mora',      'Mora'
        PAGADO    = 'pagado',    'Pagado'
        CANCELADO = 'cancelado', 'Cancelado'

    class Frecuencia(models.TextChoices):
        SEMANAL   = 'semanal',   'Semanal'
        QUINCENAL = 'quincenal', 'Quincenal'
        MENSUAL   = 'mensual',   'Mensual'

    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente            = models.ForeignKey('Cliente', on_delete=models.RESTRICT, related_name='prestamos')
    cartera            = models.ForeignKey('Cartera', on_delete=models.CASCADE, related_name='prestamos')
    monto              = models.DecimalField(max_digits=12, decimal_places=2)

    interes            = models.ForeignKey('Interes', on_delete=models.PROTECT, related_name='prestamos')
    cuotas_totales     = models.PositiveIntegerField(help_text="Número total de cuotas")
    frecuencia         = models.CharField(max_length=16, choices=Frecuencia.choices, default=Frecuencia.MENSUAL)
    primera_cuota_fecha= models.DateField(help_text="Fecha del primer cobro")

    fecha_desembolso   = models.DateField(auto_now_add=True)
    estado             = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)

    # saldos (para mostrar rápido en UI)
    saldo_capital      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_interes      = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prestamos'
        indexes = [
            models.Index(fields=['cartera'],    name='idx_prestamos_cartera'),
            models.Index(fields=['cliente'],    name='idx_prestamos_cliente'),
            models.Index(fields=['estado'],     name='idx_prestamos_estado'),
            models.Index(fields=['created_at'], name='idx_prestamos_created'),
        ]

    def __str__(self):
        return f'{self.cliente} – {self.monto} ({self.estado})'
class Cuota(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        MORA      = 'mora',      'Mora'
        PAGADA    = 'pagada',    'Pagada'
        CANCELADA = 'cancelada', 'Cancelada'

    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prestamo           = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='cuotas')
    numero             = models.PositiveIntegerField()  # 1..N
    fecha_vencimiento  = models.DateField()

    capital_programado = models.DecimalField(max_digits=12, decimal_places=2)
    interes_programado = models.DecimalField(max_digits=12, decimal_places=2)

    capital_pagado     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    interes_pagado     = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    estado             = models.CharField(max_length=16, choices=Estado.choices, default=Estado.PENDIENTE)

    class Meta:
        db_table = 'cuotas'
        unique_together = ('prestamo', 'numero')
        indexes = [
            models.Index(fields=['prestamo', 'numero'], name='idx_cuota_prestamo_num'),
            models.Index(fields=['prestamo', 'estado'], name='idx_cuota_prestamo_estado'),
        ]

    def __str__(self):
        return f'Cuota {self.numero} de {self.prestamo_id}'

    @property
    def saldo_capital(self):
        return self.capital_programado - self.capital_pagado

    @property
    def saldo_interes(self):
        return self.interes_programado - self.interes_pagado
class Pago(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prestamo    = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='pagos')
    fecha_pago  = models.DateField()  # <- no auto_now_add
    monto       = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = models.CharField(max_length=50, blank=True, default='')
    observacion = models.CharField(max_length=255, blank=True, default='')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pagos'
        indexes  = [models.Index(fields=['prestamo', 'fecha_pago'], name='idx_pagos_prestamo_fecha')]

    def __str__(self):
        return f'Pago {self.monto} a {self.prestamo_id}'
class PagoDetalle(models.Model):
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pago             = models.ForeignKey(Pago, on_delete=models.CASCADE, related_name='detalles')
    cuota            = models.ForeignKey(Cuota, on_delete=models.CASCADE, related_name='aplicaciones')
    capital_aplicado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    interes_aplicado = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'pagos_detalle'
        indexes  = [models.Index(fields=['cuota'], name='idx_pago_detalle_cuota')]
