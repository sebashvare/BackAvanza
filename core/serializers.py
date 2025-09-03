# core/serializers.py
from rest_framework import serializers
from .models import Cliente, Cartera, CarteraMiembro, Prestamo, Pago
from django.contrib.auth import get_user_model

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
        total_capital = obj.pagos.aggregate(s=models.Sum('capital_pagado'))['s'] or 0
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