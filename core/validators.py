import pandas as pd

def _norm_col(c):
    return str(c).strip().lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")

def validar_maestro(maestro_path):
    errores = []
    advertencias = []

    try:
        xls = pd.ExcelFile(maestro_path)
    except Exception as e:
        return False, [f"No pude abrir el Excel del maestro. Error: {e}"], []

    hojas_requeridas = ["Productos", "Aliases", "Exclusiones", "Configuración"]
    hojas = set(xls.sheet_names)

    for hoja in hojas_requeridas:
        if hoja not in hojas:
            errores.append(f"Falta la hoja obligatoria: {hoja}")

    if errores:
        return False, errores, advertencias

    try:
        productos = pd.read_excel(maestro_path, sheet_name="Productos")
        cols = {_norm_col(c): c for c in productos.columns}

        requeridas_productos = ["producto base", "codigo compra", "producto compra", "compra minima"]

        for req in requeridas_productos:
            if req not in cols:
                errores.append(f"Hoja Productos: falta columna '{req}'.")

        if "producto base" in cols:
            vacios = productos[cols["producto base"]].isna().sum()
            if vacios > 0:
                advertencias.append(f"Hoja Productos: hay {vacios} filas sin Producto Base.")

        if "compra minima" in cols:
            compra_min = pd.to_numeric(productos[cols["compra minima"]], errors="coerce")
            invalidos = compra_min.isna().sum()
            if invalidos > 0:
                advertencias.append(f"Hoja Productos: hay {invalidos} compras mínimas vacías o no numéricas.")

    except Exception as e:
        errores.append(f"No pude validar la hoja Productos. Error: {e}")

    try:
        aliases = pd.read_excel(maestro_path, sheet_name="Aliases")
        cols = {_norm_col(c): c for c in aliases.columns}
        if not ("alias detectado" in cols or "alias" in cols or "nombre original" in cols):
            errores.append("Hoja Aliases: falta columna de alias.")
        if "producto base" not in cols:
            errores.append("Hoja Aliases: falta columna 'Producto Base'.")
    except Exception as e:
        errores.append(f"No pude validar la hoja Aliases. Error: {e}")

    try:
        exclusiones = pd.read_excel(maestro_path, sheet_name="Exclusiones")
        if exclusiones.shape[1] < 1:
            errores.append("Hoja Exclusiones: debe tener al menos una columna.")
    except Exception as e:
        errores.append(f"No pude validar la hoja Exclusiones. Error: {e}")

    try:
        config = pd.read_excel(maestro_path, sheet_name="Configuración")
        cols = {_norm_col(c): c for c in config.columns}
        if "parametro" not in cols or "valor" not in cols:
            errores.append("Hoja Configuración: debe tener columnas Parámetro y Valor.")
    except Exception as e:
        errores.append(f"No pude validar la hoja Configuración. Error: {e}")

    return len(errores) == 0, errores, advertencias\n