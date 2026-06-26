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
