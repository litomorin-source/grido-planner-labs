from openpyxl import load_workbook

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

def _headers(ws):
    return {
        _norm_col(cell.value): idx
        for idx, cell in enumerate(ws[1], start=1)
        if cell.value is not None and str(cell.value).strip() != ""
    }

def _cell_text(value):
    return str(value or "").strip()

def validar_maestro(maestro_path):
    errores = []
    advertencias = []

    try:
        wb = load_workbook(maestro_path, read_only=True, data_only=True)
    except Exception as e:
        return False, [f"No pude abrir el Excel del maestro. Error: {e}"], []

    hojas_requeridas = ["Productos", "Aliases", "Exclusiones", "Configuración"]
    hojas = set(wb.sheetnames)

    for hoja in hojas_requeridas:
        if hoja not in hojas:
            errores.append(f"Falta la hoja obligatoria: {hoja}")

    if errores:
        wb.close()
        return False, errores, advertencias

    # PRODUCTOS
    ws = wb["Productos"]
    cols = _headers(ws)

    requeridas_productos = [
        "producto base",
        "codigo compra",
        "producto compra",
        "compra minima",
    ]

    for req in requeridas_productos:
        if req not in cols:
            errores.append(f"Hoja Productos: falta columna '{req}'.")

    if not errores:
        col_producto = cols["producto base"]
        col_codigo = cols["codigo compra"]
        col_prod_compra = cols["producto compra"]
        col_minima = cols["compra minima"]

        filas_validas = 0
        codigos_validos = 0
        compras_minimas_validas = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            producto = row[col_producto - 1] if len(row) >= col_producto else None
            codigo = row[col_codigo - 1] if len(row) >= col_codigo else None
            prod_compra = row[col_prod_compra - 1] if len(row) >= col_prod_compra else None
            compra_min = row[col_minima - 1] if len(row) >= col_minima else None

            if _cell_text(producto) or _cell_text(codigo) or _cell_text(prod_compra):
                filas_validas += 1

            if _cell_text(codigo):
                codigos_validos += 1

            try:
                if compra_min is not None and float(compra_min) > 0:
                    compras_minimas_validas += 1
            except Exception:
                pass

        if filas_validas < 5:
            errores.append("Hoja Productos: hay muy pocas filas válidas. No parece ser el Maestro real.")

        if codigos_validos < 5:
            errores.append("Hoja Productos: hay muy pocos códigos de compra válidos.")

        if compras_minimas_validas < 5:
            errores.append("Hoja Productos: hay muy pocas compras mínimas numéricas válidas.")

    # ALIASES
    ws = wb["Aliases"]
    cols = _headers(ws)

    if not ("alias detectado" in cols or "alias" in cols or "nombre original" in cols):
        errores.append("Hoja Aliases: falta columna de alias.")

    if "producto base" not in cols:
        errores.append("Hoja Aliases: falta columna 'Producto Base'.")

    # CONFIGURACION
    ws = wb["Configuración"]
    cols = _headers(ws)

    if "parametro" not in cols or "valor" not in cols:
        errores.append("Hoja Configuración: debe tener columnas Parámetro y Valor.")
    else:
        col_param = cols["parametro"]
        parametros = set()

        for row in ws.iter_rows(min_row=2, values_only=True):
            val = row[col_param - 1] if len(row) >= col_param else None
            if _cell_text(val):
                parametros.add(_cell_text(val).lower())

        esperados = {
            "semanas objetivo",
            "tiempo de reposición",
            "tiempo de reposicion",
            "días analizados",
            "dias analizados",
        }

        if len(parametros.intersection(esperados)) < 2:
            errores.append("Hoja Configuración: no encontré parámetros esperados del Maestro.")

    wb.close()
    return len(errores) == 0, errores, advertencias


def validar_carrito(carrito_path):
    errores = []
    advertencias = []

    try:
        wb = load_workbook(carrito_path, read_only=True, data_only=True)
    except Exception as e:
        return False, [f"No pude abrir el Excel del carrito. Error: {e}"], []

    if len(wb.sheetnames) < 1:
        wb.close()
        return False, ["El carrito debe tener al menos una hoja."], []

    ws = wb[wb.sheetnames[0]]

    if ws.max_row < 5:
        errores.append("El carrito no tiene datos suficientes.")
    if ws.max_column < 9:
        errores.append("El carrito debe tener al menos 9 columnas. Se espera código en columna B y precio en columna I.")

    if errores:
        wb.close()
        return False, errores, advertencias

    codigos_validos = 0
    precios_validos = 0
    filas_validas = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        codigo = row[1] if len(row) >= 2 else None
        descripcion = row[2] if len(row) >= 3 else None
        precio = row[8] if len(row) >= 9 else None

        codigo_txt = _cell_text(codigo)
        descripcion_txt = _cell_text(descripcion)

        # Código esperado: numérico o casi numérico, no texto libre.
        codigo_ok = False
        if codigo_txt:
            try:
                codigo_float = float(codigo_txt)
                if codigo_float > 1000:
                    codigo_ok = True
            except Exception:
                if codigo_txt.isdigit() and len(codigo_txt) >= 4:
                    codigo_ok = True

        precio_ok = False
        try:
            if precio is not None and _cell_text(precio) != "" and float(precio) > 0:
                precio_ok = True
        except Exception:
            pass

        if codigo_ok:
            codigos_validos += 1

        if precio_ok:
            precios_validos += 1

        if codigo_ok and precio_ok and descripcion_txt:
            filas_validas += 1

    if codigos_validos < 5:
        errores.append("No encontré suficientes códigos válidos en la columna B.")

    if precios_validos < 5:
        errores.append("No encontré suficientes precios numéricos válidos en la columna I.")

    if filas_validas < 5:
        errores.append("El archivo no parece ser el Modelo de Carrito real: faltan filas con código, descripción y precio.")

    if codigos_validos != precios_validos:
        advertencias.append(f"Códigos válidos: {codigos_validos}. Precios válidos: {precios_validos}. Revisar filas incompletas.")

    wb.close()
    return len(errores) == 0, errores, advertencias
