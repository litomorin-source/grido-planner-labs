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


def costos_a_excel(detalle, indicadores=None):
    """Exporta números reales, filtros y moneda sin alterar los cálculos."""
    from io import BytesIO
    salida = BytesIO()
    with pd.ExcelWriter(salida, engine='openpyxl') as writer:
        if indicadores is not None:
            indicadores.to_excel(writer, sheet_name='Resumen', index=False)
        detalle.drop(columns=['clave'], errors='ignore').to_excel(writer, sheet_name='Detalle', index=False)
        for ws in writer.book:
            ws.freeze_panes = 'A2'
            ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(55, max(15, max(len(str(c.value or '')) for c in col) + 2))
        formatear_monedas_excel(writer.book)
    return salida.getvalue()
