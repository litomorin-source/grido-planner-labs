"""Huella reproducible de los insumos que determinan un resultado."""
import hashlib
import json


def huella_analisis(archivos, parametros, omisiones):
    contenido = {
        "archivos": {k: hashlib.sha256(v).hexdigest() for k, v in archivos.items()},
        "parametros": {k: float(v) for k, v in parametros.items()},
        "omisiones": sorted({str(x.get("producto_base", "")).strip() for x in omisiones}),
    }
    return hashlib.sha256(json.dumps(contenido, sort_keys=True).encode()).hexdigest()


def invalidar_si_cambio(estado, huella):
    anterior = estado.get("huella_insumos_labs")
    claves = ("pedido_descargas_labs", "ultimo_analisis_snapshot",
              "costos_mix_actual", "informe_stock_bytes_260")
    cambio = anterior != huella and (anterior is not None or any(k in estado for k in claves))
    if cambio:
        for clave in ("pedido_descargas_labs", "ultimo_analisis_snapshot",
                      "costos_mix_actual", "informe_stock_bytes_260"):
            estado.pop(clave, None)
    estado["huella_insumos_labs"] = huella
    return cambio
