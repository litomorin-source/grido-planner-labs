import pandas as pd


def _norm_col(c):
    return (
        str(c or "")
        .strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )


def _find_col(df, candidates):
    cols = {_norm_col(c): c for c in df.columns}
    for c in candidates:
        key = _norm_col(c)
        if key in cols:
            return cols[key]
    return None


def _read_productos(path):
    df = pd.read_excel(path, sheet_name="Productos")
    df.columns = [str(c).strip() for c in df.columns]

    col_producto = _find_col(df, ["Producto Base", "Producto"])
    col_codigo = _find_col(df, ["Código Compra", "Codigo Compra"])
    col_producto_compra = _find_col(df, ["Producto Compra", "Descripción Compra", "Descripcion Compra"])
    col_minima = _find_col(df, ["Compra Mínima", "Compra Minima"])
    col_activo = _find_col(df, ["Activo"])
    col_excluir = _find_col(df, ["Excluir"])
    col_tipo = _find_col(df, ["Tipo Producto", "Tipo"])

    required = [col_producto, col_codigo, col_producto_compra, col_minima]
    if any(c is None for c in required):
        raise ValueError("No pude leer Productos: faltan columnas base.")

    out = pd.DataFrame()
    out["Producto Base"] = df[col_producto].astype(str).str.strip()
    out["Producto Key"] = out["Producto Base"].str.lower().str.strip()
    out["Código Compra"] = df[col_codigo].astype(str).str.strip()
    out["Producto Compra"] = df[col_producto_compra].astype(str).str.strip()
    out["Compra Mínima"] = pd.to_numeric(df[col_minima], errors="coerce")
    out["Activo"] = df[col_activo].astype(str).str.strip() if col_activo else ""
    out["Excluir"] = df[col_excluir].astype(str).str.strip() if col_excluir else ""
    out["Tipo Producto"] = df[col_tipo].astype(str).str.strip() if col_tipo else ""

    out = out[out["Producto Key"].notna() & (out["Producto Key"] != "") & (out["Producto Key"] != "nan")]
    out = out.drop_duplicates(subset=["Producto Key"], keep="first")
    return out


def comparar_maestros(maestro_actual_path, maestro_nuevo_path):
    actual = _read_productos(maestro_actual_path)
    nuevo = _read_productos(maestro_nuevo_path)

    actual_keys = set(actual["Producto Key"])
    nuevo_keys = set(nuevo["Producto Key"])

    agregados = nuevo[nuevo["Producto Key"].isin(nuevo_keys - actual_keys)].copy()
    eliminados = actual[actual["Producto Key"].isin(actual_keys - nuevo_keys)].copy()

    comunes = sorted(actual_keys.intersection(nuevo_keys))

    actual_i = actual.set_index("Producto Key")
    nuevo_i = nuevo.set_index("Producto Key")

    campos = [
        "Código Compra",
        "Producto Compra",
        "Compra Mínima",
        "Activo",
        "Excluir",
        "Tipo Producto",
    ]

    cambios_rows = []

    for key in comunes:
        prod_nombre = nuevo_i.loc[key, "Producto Base"]

        for campo in campos:
            a = actual_i.loc[key, campo] if campo in actual_i.columns else ""
            n = nuevo_i.loc[key, campo] if campo in nuevo_i.columns else ""

            a_txt = "" if pd.isna(a) else str(a).strip()
            n_txt = "" if pd.isna(n) else str(n).strip()

            if campo == "Compra Mínima":
                try:
                    a_cmp = float(a) if not pd.isna(a) else None
                except Exception:
                    a_cmp = None
                try:
                    n_cmp = float(n) if not pd.isna(n) else None
                except Exception:
                    n_cmp = None

                changed = a_cmp != n_cmp
            else:
                changed = a_txt != n_txt

            if changed:
                cambios_rows.append({
                    "Producto": prod_nombre,
                    "Campo": campo,
                    "Valor anterior": a_txt,
                    "Valor nuevo": n_txt,
                })

    cambios = pd.DataFrame(cambios_rows)

    resumen = {
        "productos_actual": len(actual),
        "productos_nuevo": len(nuevo),
        "agregados": len(agregados),
        "eliminados": len(eliminados),
        "cambios": len(cambios),
    }

    return {
        "resumen": resumen,
        "agregados": agregados[["Producto Base", "Código Compra", "Producto Compra", "Compra Mínima", "Activo", "Excluir", "Tipo Producto"]].rename(columns={"Producto Base": "Producto"}),
        "eliminados": eliminados[["Producto Base", "Código Compra", "Producto Compra", "Compra Mínima", "Activo", "Excluir", "Tipo Producto"]].rename(columns={"Producto Base": "Producto"}),
        "cambios": cambios,
    }
