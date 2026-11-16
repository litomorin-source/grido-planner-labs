"""Una fecha orientativa, editable, para la proyección de cámara."""
from datetime import timedelta


def miercoles_semana_siguiente(fecha_pedido):
    return fecha_pedido + timedelta(days=9 - fecha_pedido.weekday())


def semanas_hasta_recepcion(fecha_stock, fecha_recepcion):
    dias = (fecha_recepcion - fecha_stock).days
    if dias < 0:
        raise ValueError("La llegada estimada no puede ser anterior al stock cargado.")
    return dias / 7.0
