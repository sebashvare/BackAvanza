# apps/cobros/services.py
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.db import transaction
from .models import Prestamo, Cuota, Pago, PagoDetalle

def _recalcular_saldos_prestamo(prestamo: Prestamo):
    qs = prestamo.cuotas.all()
    prestamo.saldo_capital = _r2(sum((c.saldo_capital for c in qs), Decimal(0)))
    prestamo.saldo_interes = _r2(sum((c.saldo_interes for c in qs), Decimal(0)))
    prestamo.save(update_fields=['saldo_capital', 'saldo_interes'])

    if prestamo.saldo_capital == 0 and prestamo.saldo_interes == 0:
        nuevo = Prestamo.Estado.PAGADO
    else:
        # si alguna cuota está en MORA → MORA, si no → PENDIENTE
        nuevo = Prestamo.Estado.MORA if qs.filter(estado=Cuota.Estado.MORA).exists() else Prestamo.Estado.PENDIENTE

    if prestamo.estado != nuevo:
        prestamo.estado = nuevo
        prestamo.save(update_fields=['estado'])

def actualizar_estado_por_mora(prestamo: Prestamo, hoy: date | None = None):
    hoy = hoy or date.today()
    cuotas = prestamo.cuotas.select_for_update()
    hay_mora = False

    for c in cuotas:
        if c.estado != Cuota.Estado.PAGADA and c.fecha_vencimiento < hoy:
            if c.estado != Cuota.Estado.MORA:
                c.estado = Cuota.Estado.MORA
                c.save(update_fields=['estado'])
            hay_mora = True

    if hay_mora:
        prestamo.estado = Prestamo.Estado.MORA
    else:
        # recalculamos saldo y decidimos
        _recalcular_saldos_prestamo(prestamo)
    prestamo.save(update_fields=['estado'])

def _r2(x):  # 2 decimales
    return Decimal(x).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def _next_date(freq: str, d: date) -> date:
    if freq == Prestamo.Frecuencia.SEMANAL:
        return d + relativedelta(days=7)
    if freq == Prestamo.Frecuencia.QUINCENAL:
        return d + relativedelta(days=15)
    return d + relativedelta(months=1)  # mensual

def generar_calendario(prestamo: Prestamo):
    """
    Interés plano: interes_total = monto * tasa_decimal (sobre el total).
    Se reparte capital e interés por partes iguales (última cuota ajusta).
    """
    prestamo.cuotas.all().delete()

    N = prestamo.cuotas_totales
    monto = Decimal(prestamo.monto)
    tasa  = Decimal(prestamo.interes.tasa_decimal)

    interes_total = _r2(monto * tasa)
    capital_cuota = monto / N
    interes_cuota = interes_total / N

    caps = [_r2(capital_cuota)] * (N - 1)
    ints = [_r2(interes_cuota)] * (N - 1)
    caps.append(_r2(monto - sum(caps, Decimal(0))))
    ints.append(_r2(interes_total - sum(ints, Decimal(0))))

    fecha = prestamo.primera_cuota_fecha

    with transaction.atomic():
        for i in range(N):
            Cuota.objects.create(
                prestamo=prestamo,
                numero=i + 1,
                fecha_vencimiento=fecha,
                capital_programado=caps[i],
                interes_programado=ints[i],
            )
            fecha = _next_date(prestamo.frecuencia, fecha)

        _recalcular_saldos_prestamo(prestamo)

def aplicar_pago(pago: Pago):
    prestamo = pago.prestamo
    monto = Decimal(pago.monto)

    with transaction.atomic():
        actualizar_estado_por_mora(prestamo)

        cuotas = (prestamo.cuotas
                  .select_for_update()
                  .filter(estado__in=[Cuota.Estado.PENDIENTE, Cuota.Estado.MORA])
                  .order_by('numero'))

        for c in cuotas:
            if monto <= 0:
                break

            # 1) Interés de la cuota
            a_int = min(monto, c.saldo_interes)
            monto -= a_int

            # 2) Capital de la cuota
            a_cap = min(monto, c.saldo_capital)
            monto -= a_cap

            if a_int > 0 or a_cap > 0:
                PagoDetalle.objects.create(
                    pago=pago, cuota=c,
                    interes_aplicado=_r2(a_int),
                    capital_aplicado=_r2(a_cap),
                )

                c.interes_pagado = _r2(c.interes_pagado + a_int)
                c.capital_pagado = _r2(c.capital_pagado + a_cap)

                # estado de la cuota
                if c.saldo_interes == 0 and c.saldo_capital == 0:
                    c.estado = Cuota.Estado.PAGADA
                else:
                    # si sigue vencida: MORA; si no, PENDIENTE
                    c.estado = Cuota.Estado.MORA if c.fecha_vencimiento < pago.fecha_pago else Cuota.Estado.PENDIENTE
                c.save()

        _recalcular_saldos_prestamo(prestamo)

def actualizar_estados_cuotas():
    """
    Actualiza los estados de las cuotas individuales basándose en fechas de vencimiento
    """
    from .models import Cuota
    from django.db.models import F
    
    # Cuotas que deben estar en MORA (vencidas y no pagadas completamente)
    cuotas_para_mora = Cuota.objects.filter(
        fecha_vencimiento__lt=date.today(),
        estado=Cuota.Estado.PENDIENTE
    ).annotate(
        saldo_total=F('capital_programado') + F('interes_programado') - F('capital_pagado') - F('interes_pagado')
    ).filter(saldo_total__gt=0)
    
    count_mora = cuotas_para_mora.update(estado=Cuota.Estado.MORA)
    print(f"✅ Actualizadas {count_mora} cuotas a MORA")
    
    # Cuotas que deben estar PAGADAS (sin saldo pendiente)
    cuotas_para_pagadas = Cuota.objects.filter(
        estado__in=[Cuota.Estado.PENDIENTE, Cuota.Estado.MORA]
    ).annotate(
        saldo_total=F('capital_programado') + F('interes_programado') - F('capital_pagado') - F('interes_pagado')
    ).filter(saldo_total=0)
    
    count_pagadas = cuotas_para_pagadas.update(estado=Cuota.Estado.PAGADA)
    print(f"✅ Actualizadas {count_pagadas} cuotas a PAGADA")
    
    return count_mora, count_pagadas

def actualizar_estados_prestamos():
    """
    Actualiza automáticamente los estados de los préstamos basándose en el estado de sus cuotas
    """
    from .models import Prestamo, Cuota
    from django.db.models import F
    
    count_mora = 0
    count_pagados = 0
    
    # Obtener todos los préstamos que no están en estado final
    prestamos_activos = Prestamo.objects.filter(
        estado__in=[Prestamo.Estado.PENDIENTE, Prestamo.Estado.MORA]
    ).prefetch_related('cuotas')
    
    for prestamo in prestamos_activos:
        # Verificar si tiene cuotas en mora
        tiene_cuotas_mora = prestamo.cuotas.filter(
            estado=Cuota.Estado.MORA
        ).exists()
        
        # Verificar si todas las cuotas están pagadas
        cuotas_pendientes = prestamo.cuotas.filter(
            estado__in=[Cuota.Estado.PENDIENTE, Cuota.Estado.MORA]
        ).annotate(
            saldo_total=F('capital_programado') + F('interes_programado') - F('capital_pagado') - F('interes_pagado')
        ).filter(saldo_total__gt=0)
        
        # Actualizar estado según corresponda
        if not cuotas_pendientes.exists():
            # Todas las cuotas están pagadas
            if prestamo.estado != Prestamo.Estado.PAGADO:
                prestamo.estado = Prestamo.Estado.PAGADO
                prestamo.save(update_fields=['estado'])
                count_pagados += 1
                print(f"✅ Préstamo {prestamo.id} actualizado a PAGADO")
                
        elif tiene_cuotas_mora and prestamo.estado != Prestamo.Estado.MORA:
            # Tiene cuotas en mora
            prestamo.estado = Prestamo.Estado.MORA
            prestamo.save(update_fields=['estado'])
            count_mora += 1
            print(f"⚠️  Préstamo {prestamo.id} actualizado a MORA")
    
    print(f"📊 Resumen: {count_mora} préstamos a MORA, {count_pagados} préstamos PAGADOS")
    return count_mora, count_pagados
