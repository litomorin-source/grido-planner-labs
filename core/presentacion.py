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
