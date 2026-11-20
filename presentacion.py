"""Formato de pantalla; nunca modifica cantidades usadas en cálculos."""
import pandas as pd


def formato_bultos(valor):
    if valor is None or pd.isna(valor):
        return "—"
    return f"{round(float(valor)):,}".replace(",", ".")


def formatear_bultos(tabla):
    resultado = tabla.copy()
    for col in resultado.columns:
        if "bultos" in str(col).lower():
            resultado[col] = resultado[col].map(formato_bultos)
    return resultado


def formatear_monedas_excel(libro):
    """Aplica formato numérico de pesos sin convertir valores ni tocar cantidades."""
    import unicodedata
    def normalizar(texto):
        return ''.join(c for c in unicodedata.normalize('NFD', str(texto).lower().strip())
                       if unicodedata.category(c) != 'Mn')
    for hoja in libro.worksheets:
        for fila in hoja.iter_rows():
            for celda in fila:
                if not isinstance(celda.value, str):
                    continue
                nombre = normalizar(celda.value)
                monetaria = (nombre.startswith(('precio', 'costo', 'importe', 'valor stock', 'valor pedido', 'valor del stock'))
                             or nombre in {'valor', 'valor_stock', 'valor unitario', 'total valorizado'})
                if not monetaria or any(t in nombre for t in ('%', 'variacion', 'fecha', 'origen', 'sin costo', 'sin precio')):
                    continue
                for siguientes in hoja.iter_rows(min_row=celda.row+1, min_col=celda.column, max_col=celda.column):
                    dato = siguientes[0]
                    if nombre == 'valor':
                        concepto = normalizar(hoja.cell(dato.row, max(1, dato.column-1)).value)
                        if not concepto.startswith(('valor stock', 'subtotal stock', 'costo', 'importe', 'precio')):
                            continue
                    if isinstance(dato.value, (int, float)) and not isinstance(dato.value, bool):
                        dato.number_format = '"$ "#,##0.00;[Red]"-$ "#,##0.00;"$ "0.00'
