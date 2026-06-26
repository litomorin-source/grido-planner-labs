from openpyxl import load_workbook

def _norm_col(c):
    return str(c or "").strip().lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")

def _headers(ws):
    return {_norm_col(cell.value): idx for idx, cell in enumerate(ws[1], start=1) if cell.value is not None}

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

    ws = wb["Productos"]
    cols = _headers(ws)

    for req in ["producto base", "codigo compra", "producto compra", "compra minima"]:
        if req not in cols:
            errores.append(f"Hoja Productos: falta columna '{req}'.")

    if "producto base" in cols:
        col = cols["producto base"]
        vacios = 0
        for row in ws.iter_rows(min_row=2, min_col=col, max_col=col, values_only=True):
            if row[0] is None or str(row[0]).strip() == "":
                vacios += 1
        if vacios:
            advertencias.append(f"Hoja Productos: hay {vacios} filas sin Producto Base.")

    ws = wb["Aliases"]
    cols = _headers(ws)
    if not ("alias detectado" in cols or "alias" in cols or "nombre original" in cols):
        errores.append("Hoja Aliases: falta columna de alias.")
    if "producto base" not in cols:
        errores.append("Hoja Aliases: falta columna 'Producto Base'.")

    ws = wb["Exclusiones"]
    if ws.max_column < 1:
        errores.append("Hoja Exclusiones: debe tener al menos una columna.")

    ws = wb["Configuración"]
    cols = _headers(ws)
    if "parametro" not in cols or "valor" not in cols:
        errores.append("Hoja Configuración: debe tener columnas Parámetro y Valor.")

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

    if ws.max_row < 2:
        errores.append("El carrito no tiene datos suficientes.")
    if ws.max_column < 9:
        errores.append("El carrito debe tener al menos 9 columnas. Se espera código en columna B y precio en columna I.")

    if errores:
        wb.close()
        return False, errores, advertencias

    codigos_validos = 0
    precios_validos = 0
    filas_con_datos = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        codigo = row[1] if len(row) >= 2 else None
        precio = row[8] if len(row) >= 9 else None

        tiene_datos = any(cell is not None and str(cell).strip() != "" for cell in row)
        if tiene_datos:
            filas_con_datos += 1

        if codigo is not None and str(codigo).strip() != "":
            codigos_validos += 1

        try:
            if precio is not None and str(precio).strip() != "":
                float(precio)
                precios_validos += 1
        except Exception:
            pass

    if filas_con_datos == 0:
        errores.append("El carrito no contiene filas con datos.")

    if codigos_validos == 0:
        errores.append("No encontré códigos válidos en la columna B.")

    if precios_validos == 0:
        errores.append("No encontré precios numéricos válidos en la columna I.")

    if codigos_validos > 0 and precios_validos > 0 and codigos_validos != precios_validos:
        advertencias.append(f"Códigos válidos: {codigos_validos}. Precios válidos: {precios_validos}. Revisar si hay filas incompletas.")

    wb.close()
    return len(errores) == 0, errores, advertencias
