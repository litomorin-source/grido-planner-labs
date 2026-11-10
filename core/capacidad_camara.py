"""Bultos operativos de SmartFran y capacidad proyectada de la cámara.

IMPORTANTE:
- Stock: columna Bultos NETOS, sin recortar negativos. Las aperturas de caja
  no registradas generan stock negativo de unidades que compensa cajas cerradas.
- Pedido: cada pack de compra del Maestro corresponde a un bulto de recepción.
- Consumo proyectado: reutiliza la Venta Semanal del motor y Compra Mínima.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd


# Alcance calibrado con Stock_20261105_105903.csv: 980,98 bultos netos.
# No incluye Smoothie, GIO, Gridos M. Prima., insumos ni descartables.
GRUPOS_CONGELADOS = {"Congelados Multimarca", "Frizzio"}
CAPACIDAD_REFERENCIA = 980.98


def _decimal_ar(series):
    return pd.to_numeric(
        series.astype(str).str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False), errors="coerce"
    ).fillna(0.0)


def leer_bultos_stock(stock_path):
    """Devuelve total neto, desglose de grupos y líneas de stock de la cámara."""
    df = pd.read_csv(Path(stock_path), sep=";", encoding="utf-8-sig", dtype=str)
    obligatorias = {"Rubro", "SubRubro", "Grupo", "Bultos"}
    faltantes = obligatorias - set(df.columns)
    if faltantes:
        raise ValueError("El CSV de stock no tiene las columnas: " + ", ".join(sorted(faltantes)))
    mask = (
        ((df["Rubro"] == "Heladería")
         & df["SubRubro"].isin(["Sabores", "Impulsivos"])
         & (df["Grupo"] != "Gridos M. Prima."))
        | ((df["Rubro"] == "Congelados") & df["Grupo"].isin(GRUPOS_CONGELADOS))
    )
    camara = df.loc[mask].copy()
    camara["Bultos netos"] = _decimal_ar(camara["Bultos"])
    por_grupo = (camara.groupby("Grupo", as_index=False)["Bultos netos"]
                 .sum().sort_values("Bultos netos", ascending=False))
    total = float(camara["Bultos netos"].sum())
    positivos = float(camara["Bultos netos"].clip(lower=0).sum())
    negativos = float(camara["Bultos netos"].clip(upper=0).sum())
    return {
        "netos": total, "positivos": positivos, "negativos": negativos,
        "por_grupo": por_grupo, "filas": camara,
    }


def proyectar_capacidad(pedido, bultos_actuales, dias_analizados, semanas_reposicion,
                        capacidad_maxima=CAPACIDAD_REFERENCIA):
    """Estima mercadería que queda al recibir, con el mix vigente del pedido.

    Para cada producto se descuenta como máximo el stock neto positivo de ese
    producto. Así, la proyección no supone vender mercadería inexistente.
    Los productos sin equivalencia/código no generan compra ficticia.
    """
    if pedido is None or pedido.empty:
        raise ValueError("Generá un pedido primero para proyectar la recepción.")
    dias = float(semanas_reposicion) * 7.0
    if dias_analizados <= 0 or dias < 0:
        raise ValueError("Revisá los días analizados y el tiempo de reposición.")
    df = pedido.copy()
    col_ventas = next((c for c in df.columns if str(c).startswith("Ventas ") and str(c).endswith(" días")), None)
    if col_ventas is None:
        raise ValueError("No se encontró la columna de ventas del período en el pedido.")

    for col in ["Stock", "Compra Mínima", "Packs a Comprar", col_ventas]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Compra Mínima"] = df["Compra Mínima"].where(df["Compra Mínima"] > 0)

    # Productos de congelados incluidos en la calibración, evitando insumos y
    # otros rubros. Helado = grupo de sabores.
    grupos = {"Helado", "Bombones", "Familiar", "Líneas Especiales C. Heladas",
              "Palitos", "Postres", "Tentación", "Tortas", *GRUPOS_CONGELADOS}
    df = df[df["Grupo"].isin(grupos)].copy()
    codigo = df["Código Compra"].astype(str).str.strip()
    valido = df["Compra Mínima"].notna() & codigo.ne("") & ~codigo.str.lower().isin(["nan", "none"])

    # Dato del motor: ventas del período en unidades equivalentes, antes de convertir
    # a bultos de recepción del proveedor.
    df["Consumo semanal (eq)"] = (df[col_ventas].fillna(0).clip(lower=0)
                                    / float(dias_analizados) * 7)
    df["Consumo hasta recepción (eq)"] = df["Consumo semanal (eq)"] * float(semanas_reposicion)
    # No descontar más unidades de las que hay disponibles de cada producto.
    disponible = df["Stock"].fillna(0).clip(lower=0)
    df["Consumo descontado (eq)"] = pd.concat(
        [df["Consumo hasta recepción (eq)"], disponible], axis=1
    ).min(axis=1)
    df["Consumo descontado (bultos)"] = 0.0
    df.loc[valido, "Consumo descontado (bultos)"] = (
        df.loc[valido, "Consumo descontado (eq)"] / df.loc[valido, "Compra Mínima"]
    )
    df["Bultos a recibir"] = 0.0
    df.loc[valido, "Bultos a recibir"] = df.loc[valido, "Packs a Comprar"].fillna(0).clip(lower=0)

    consumo = float(df["Consumo descontado (bultos)"].sum())
    compra = float(df["Bultos a recibir"].sum())
    proyectados = float(bultos_actuales) - consumo + compra
    capacidad = float(capacidad_maxima)
    cobertura = 100 * proyectados / capacidad if capacidad > 0 else None
    return {
        "dias_hasta_recepcion": dias,
        "consumo_esperado_bultos": consumo,
        "pedido_bultos": compra,
        "bultos_al_recibir": proyectados,
        "capacidad_bultos": capacidad,
        "ocupacion_pct": cobertura,
        "sin_conversion": int((~valido).sum()),
        "detalle": df[["Grupo", "Producto", "Stock", col_ventas,
                        "Consumo hasta recepción (eq)", "Consumo descontado (bultos)",
                        "Packs a Comprar", "Bultos a recibir"]].copy(),
    }
