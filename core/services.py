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
