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


def leer_bultos_stock(stock_path, maestro_path=None):
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
    if maestro_path is not None:
        import motor
        productos = motor.load_productos(maestro_path).set_index('Producto Base').to_dict('index')
        aliases = {r['Alias Normalizado']: r.to_dict() for _, r in motor.load_aliases(maestro_path).iterrows()}
        excluidos = motor.load_exclusiones(maestro_path)
        bases = camara['Item'].map(lambda nombre: motor.alias_lookup(nombre, aliases)['Producto Base'])
        incluido = ~bases.isin(excluidos) & ~camara['Item'].map(motor.normalize).isin(excluidos)
        incluido &= ~camara['Item'].astype(str).str.contains('desactivado', case=False, na=False)
        camara = camara.loc[incluido].copy()
        camara['Bultos SmartFran'] = camara['Bultos netos']
        cantidades = _decimal_ar(camara['Stock'])
        bultos = []
        for (_, row), cantidad in zip(camara.iterrows(), cantidades):
            info = motor.alias_lookup(row['Item'], aliases)
            base = info['Producto Base']
            minima = motor.safe_num(productos.get(base, {}).get('Compra Mínima'), 0)
            eq, _ = motor.convert_quantity(row['Item'], base, cantidad, info.get('Tipo Presentación', ''), info.get('Pack Detectado'), productos)
            bultos.append(eq / minima if minima > 0 else float('nan'))
        camara['Bultos netos'] = bultos
    por_grupo = (camara.groupby("Grupo", as_index=False)["Bultos netos"]
                 .sum().sort_values("Bultos netos", ascending=False))
    total = float(camara["Bultos netos"].sum())
    positivos = float(camara["Bultos netos"].clip(lower=0).sum())
    negativos = float(camara["Bultos netos"].clip(upper=0).sum())
    return {
        "netos": total, "positivos": positivos, "negativos": negativos,
        "sin_conversion": int(camara["Bultos netos"].isna().sum()),
        "por_grupo": por_grupo, "filas": camara,
    }


def preparar_movimientos_camara(stock_path, maestro_path):
    """Separa físico/tránsito con las equivalencias del maestro original.

    Las omisiones de compra no eliminan mercadería de la cámara. Un artículo
    sin equivalencia queda pendiente, nunca se le inventa un volumen.
    """
    import motor
    productos = motor.load_productos(maestro_path)
    productos_map = productos.set_index("Producto Base").to_dict(orient="index")
    aliases = motor.load_aliases(maestro_path)
    alias_map = {r["Alias Normalizado"]: r.to_dict() for _, r in aliases.iterrows()}
    filas = leer_bultos_stock(stock_path, maestro_path)["filas"].copy()
    for col in ("Stock", "Tránsito"):
        filas[col] = _decimal_ar(filas[col]) if col in filas else 0.0
    resultado = []
    for _, row in filas.iterrows():
        raw = str(row["Item"])
        info = motor.alias_lookup(raw, alias_map)
        base = info["Producto Base"]
        minima = motor.safe_num(productos_map.get(base, {}).get("Compra Mínima"), 0)
        fisico, _ = motor.convert_quantity(raw, base, row["Stock"], info.get("Tipo Presentación", ""), info.get("Pack Detectado"), productos_map)
        transito, _ = motor.convert_quantity(raw, base, row["Tránsito"], info.get("Tipo Presentación", ""), info.get("Pack Detectado"), productos_map)
        resultado.append({"Producto": base, "Stock físico (eq)": fisico,
                          "Tránsito (eq)": transito, "Compra Mínima": minima,
                          "Tránsito sin conversión": int((minima <= 0 or pd.isna(transito)) and row["Tránsito"] != 0)})
    df = pd.DataFrame(resultado, columns=["Producto", "Stock físico (eq)", "Tránsito (eq)", "Compra Mínima", "Tránsito sin conversión"])
    return df.groupby("Producto", as_index=False).agg({
        "Stock físico (eq)": "sum", "Tránsito (eq)": "sum", "Compra Mínima": "first",
        "Tránsito sin conversión": "sum",
    })


def _proyectar_con_movimientos(pedido, movimientos, bultos_actuales, dias, semanas, capacidad, incluir_transito):
    if dias <= 0 or semanas < 0 or capacidad <= 0:
        raise ValueError("Revisá días analizados, tiempo de reposición y capacidad.")
    ventas_col = next((c for c in pedido if c.startswith("Ventas ") and c.endswith(" días")), None)
    if ventas_col is None:
        raise ValueError("No se encontró la columna de ventas del período.")
    grupos = {"Helado", "Bombones", "Familiar", "Líneas Especiales C. Heladas",
              "Palitos", "Postres", "Tentación", "Tortas", *GRUPOS_CONGELADOS}
    p = pedido[pedido["Grupo"].isin(grupos) | pedido["Producto"].isin(movimientos["Producto"])].copy()
    p = p.groupby("Producto", as_index=False).agg({ventas_col: "sum", "Packs a Comprar": "sum", "Compra Mínima": "first"})
    df = movimientos.merge(p, on="Producto", how="outer", suffixes=("", " pedido"))
    df["Compra Mínima"] = df["Compra Mínima"].fillna(df["Compra Mínima pedido"])
    for col in ("Stock físico (eq)", "Tránsito (eq)", "Tránsito sin conversión", ventas_col, "Packs a Comprar"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    factor = df["Compra Mínima"].where(df["Compra Mínima"].gt(0))
    consumo_eq = pd.concat([df[ventas_col].clip(lower=0) / dias * 7 * semanas,
                            df["Stock físico (eq)"].clip(lower=0)], axis=1).min(axis=1)
    df["Consumo descontado (bultos)"] = consumo_eq / factor
    df["Tránsito incluido (bultos)"] = df["Tránsito (eq)"] / factor if incluir_transito else 0.0
    df["Bultos a recibir"] = df["Packs a Comprar"].clip(lower=0)
    consumo = float(df["Consumo descontado (bultos)"].sum())
    transito = float(df["Tránsito incluido (bultos)"].sum())
    compra = float(df["Bultos a recibir"].sum())
    total = float(bultos_actuales) - consumo + transito + compra
    return {
        "dias_hasta_recepcion": semanas * 7, "consumo_esperado_bultos": consumo,
        "pedido_bultos": compra, "transito_bultos": transito,
        "transito_sin_conversion": int(df["Tránsito sin conversión"].sum()) if incluir_transito else 0,
        "bultos_al_recibir": total, "capacidad_bultos": capacidad,
        "ocupacion_pct": total / capacidad * 100,
        "sin_conversion": int((factor.isna() & (df["Stock físico (eq)"].ne(0) | df["Tránsito (eq)"].ne(0) | df["Packs a Comprar"].gt(0))).sum()),
        "detalle": df.drop(columns=["Compra Mínima pedido"]),
    }


def proyectar_capacidad(pedido, bultos_actuales, dias_analizados, semanas_reposicion,
                        capacidad_maxima=CAPACIDAD_REFERENCIA, movimientos_stock=None,
                        incluir_transito=True):
    """Estima mercadería que queda al recibir, con el mix vigente del pedido.

    Para cada producto se descuenta como máximo el stock neto positivo de ese
    producto. Así, la proyección no supone vender mercadería inexistente.
    Los productos sin equivalencia/código no generan compra ficticia.
    """
    if pedido is None or pedido.empty:
        raise ValueError("Generá un pedido primero para proyectar la recepción.")
    if movimientos_stock is not None:
        return _proyectar_con_movimientos(pedido, movimientos_stock, float(bultos_actuales),
                                         float(dias_analizados), float(semanas_reposicion),
                                         float(capacidad_maxima), incluir_transito)
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
