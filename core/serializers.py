# core/serializers.py
from decimal import Decimal
from rest_framework import serializers
from .models import Cliente, Cartera, CarteraMiembro, Prestamo, Pago, Interes, Prestamo, Cuota, Pago, PagoDetalle
from django.contrib.auth import get_user_model
from django.db.models import Sum 

User = get_user_model()

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'
class CarteraMiembroSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source='usuario.email', read_only=True)
    usuario_id    = serializers.PrimaryKeyRelatedField(source='usuario', read_only=True)

    class Meta:
        model  = CarteraMiembro
        fields = ('id', 'usuario_id', 'usuario_email', 'rol', 'creado')
class CarteraAsignarMiembroSerializer(serializers.Serializer):
    usuario_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='usuario')
    rol        = serializers.ChoiceField(choices=CarteraMiembro.RolEnCartera.choices, default=CarteraMiembro.RolEnCartera.GESTOR)
class CarteraSerializer(serializers.ModelSerializer):
    # Solo lectura: listamos miembros
    miembros = serializers.SerializerMethodField()

    class Meta:
        model  = Cartera
        fields = ('id', 'nombre', 'descripcion', 'miembros', 'created_at')
        read_only_fields = ('miembros', 'created_at')

    def get_miembros(self, obj: Cartera):
        asignaciones = obj.asignaciones.select_related('usuario').all()
        return CarteraMiembroSerializer(asignaciones, many=True).data
    
class PrestamoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    cartera_nombre = serializers.CharField(source='cartera.nombre', read_only=True)
    saldo          = serializers.SerializerMethodField()

    class Meta:
        model  = Prestamo
        fields = ('id','cliente','cliente_nombre','cartera','cartera_nombre',
                  'monto','interes_mensual','plazo_meses','fecha_desembolso',
                  'estado','created_at','saldo')

    def get_saldo(self, obj: Prestamo):
        # Saldo simple: monto - suma(capital_pagado)
        total_capital = obj.pagos.aggregate(s=Sum('capital_pagado'))['s'] or 0
        return float(obj.monto) - float(total_capital)

    def validate(self, data):
        if data.get('monto') is not None and data['monto'] <= 0:
            raise serializers.ValidationError('monto debe ser > 0')
        if data.get('interes_mensual') is not None and data['interes_mensual'] < 0:
            raise serializers.ValidationError('interes_mensual debe ser >= 0')
        if data.get('plazo_meses') is not None and data['plazo_meses'] <= 0:
            raise serializers.ValidationError('plazo_meses debe ser > 0')
        return data
    
class PagoSerializer(serializers.ModelSerializer):
    prestamo_info = serializers.SerializerMethodField()

    class Meta:
        model  = Pago
        fields = ('id','prestamo','prestamo_info','fecha_pago','monto',
                  'capital_pagado','interes_pagado','mora_pagada','metodo_pago','created_at')

    def get_prestamo_info(self, obj: Pago):
        return {
            'id': str(obj.prestamo_id),
            'cliente': obj.prestamo.cliente.nombre,
            'cartera': obj.prestamo.cartera.nombre
        }

    def validate(self, data):
        m  = data.get('monto', 0)
        c  = data.get('capital_pagado', 0)
        i  = data.get('interes_pagado', 0)
        mo = data.get('mora_pagada', 0)
        if m <= 0:
            raise serializers.ValidationError('monto debe ser > 0')
        if c < 0 or i < 0 or mo < 0:
            raise serializers.ValidationError('componentes del pago no pueden ser negativos')
        if (c + i + mo) > m:
            raise serializers.ValidationError('capital + interés + mora no deben exceder monto')
        return data
    
class InteresSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interes
        fields = '__all__'

class CuotaSerializer(serializers.ModelSerializer):
    saldo_capital = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    saldo_interes = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Cuota
        fields = '__all__'

class PrestamoSerializer(serializers.ModelSerializer):
    cuotas = CuotaSerializer(many=True, read_only=True)
    interes = InteresSerializer(read_only=True) 
    interes_id = serializers.PrimaryKeyRelatedField(source="interes", queryset=Interes.objects.all(), write_only=True)
    class Meta:
        model = Prestamo
        fields = "__all__"

class PagoDetalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagoDetalle
        fields = '__all__'

class PagoSerializer(serializers.ModelSerializer):
    detalles = PagoDetalleSerializer(many=True, read_only=True)
    detalles = PagoDetalleSerializer(many=True, read_only=True)

    class Meta:
        model = Pago
        fields = '__all__'

    def validate(self, attrs):
        prestamo: Prestamo = attrs.get('prestamo')
        monto = Decimal(str(attrs.get('monto', 0)))

        if prestamo is None:
            raise serializers.ValidationError("Debe indicar el préstamo.")

        # Asegúrate de tener saldos actualizados antes (opcional si los mantienes al día)
        # Si quieres, puedes recalcular aquí: _recalcular_saldos_prestamo(prestamo)

        # 1) Si el préstamo ya está pagado, rechazar
        if prestamo.estado == Prestamo.Estado.PAGADO:
            raise serializers.ValidationError("El préstamo ya está pagado. No se aceptan más pagos.")

        # 2) Si el saldo total es 0, rechazar (por si el estado aún no se actualizó)
        saldo_total = (prestamo.saldo_capital or 0) + (prestamo.saldo_interes or 0)
        if Decimal(saldo_total) <= 0:
            raise serializers.ValidationError("El préstamo no tiene saldo pendiente. No se aceptan más pagos.")

        # 3) (opcional) Evitar sobrepago: monto > saldo_total
        if monto > Decimal(saldo_total):
            raise serializers.ValidationError(
                f"El monto ({monto}) excede el saldo ({saldo_total}). "
                "Registre un pago por el saldo exacto."
            )

        if monto <= 0:
            raise serializers.ValidationError("El monto del pago debe ser mayor a 0.")

        return attrs