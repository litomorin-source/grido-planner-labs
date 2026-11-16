"""Completar productos desde Stock, preservando las demás hojas del Maestro."""
from copy import copy
from difflib import SequenceMatcher
from io import BytesIO
import math
import pandas as pd
from openpyxl import load_workbook
import motor
from core.validators import _parse_price_ar, validar_maestro

MAESTRO = 'data/Maestro_Productos_Grido.xlsx'
CARRITO = 'data/Modelo_de_Carrito.xlsx'
TIPOS = ['Sabor 7,800 kg', 'Producto cerrado', 'Fraccionable', 'Palito especial', 'Palito']


def codigo_limpio(valor):
    codigo = motor.normalizar_codigo_compra(valor)
    return '' if codigo.lower() in {'', 'nan', 'none', '<na>'} else codigo


def positivo(valor):
    n = _parse_price_ar(valor)
    return n is not None and math.isfinite(n) and n > 0


def catalogo_carrito(path):
    df = pd.read_excel(path, dtype={'Codigo': str})
    registros = []
    for _, r in df.iterrows():
        codigo = codigo_limpio(r['Codigo'])
        if not codigo:
            continue
        registros.append({'codigo': codigo, 'descripcion': str(r['Descripcion']).strip(),
                          'precio': _parse_price_ar(r['precio']),
                          'peso': _parse_price_ar(r['Peso']),
                          'cubicaje': _parse_price_ar(r['Cubicaje'])})
    return registros


def pendientes_stock(stock_path, maestro_path, carrito_path):
    productos = motor.load_productos(maestro_path)
    # El motor tolera celdas vacías con valor 1. El editor debe mostrarlas como
    # pendientes en lugar de confundir ese valor de respaldo con un dato confirmado.
    originales = pd.read_excel(maestro_path, sheet_name='Productos')
    originales.columns = [motor.normalize(c) for c in originales.columns]
    equivalencias = dict(zip(originales['producto base'].map(motor.normalize), originales['compra minima']))
    activos = productos[productos['Activo'] & ~productos['Excluir']]
    mapa = activos.set_index('Producto Base').to_dict('index')
    aliases = motor.load_aliases(maestro_path)
    alias_map = {r['Alias Normalizado']: dict(r, **{'Alias Encontrado': True})
                 for _, r in aliases.iterrows()}
    filas = motor.read_stock(stock_path, motor.load_config(maestro_path), alias_map,
                             mapa, motor.load_exclusiones(maestro_path))
    precios = motor.load_precios_carrito(carrito_path)
    salida = []
    if filas.empty:
        return salida
    for base, grupo in filas.groupby('Producto Base'):
        producto = mapa.get(base, {})
        codigo = codigo_limpio(producto.get('Código Compra'))
        motivos = []
        if not producto:
            motivos.append('Producto sin ficha activa en el Maestro')
        if not codigo:
            motivos.append('Sin código de compra')
        elif not positivo(precios.get(codigo)):
            motivos.append('Código sin precio vigente en el Carrito')
        minima = equivalencias.get(base)
        if not positivo(minima):
            motivos.append('Sin equivalencia de compra')
        if motivos:
            salida.append({'producto': base, 'codigo': codigo, 'motivo': ' · '.join(motivos),
                           'nombres': sorted(set(grupo['Nombre original'])),
                           'grupo': str(grupo.iloc[0]['Grupo']),
                           'minima': minima,
                           'tipo': producto.get('Tipo Producto', '')})
    return salida


def ordenar_candidatos(nombre, catalogo):
    """Solo ordena sugerencias; nunca elige ni vincula automáticamente."""
    tokens = set(motor.normalize(nombre).split())
    def score(r):
        desc = motor.normalize(r['descripcion'])
        return (len(tokens & set(desc.split())) / max(1, len(tokens)),
                SequenceMatcher(None, motor.normalize(nombre), desc).ratio())
    return sorted(catalogo, key=score, reverse=True)


def _cabeceras(ws):
    return {motor.normalize(c.value): c.column for c in ws[1] if c.value is not None}


def _fila_nueva(ws):
    fila = ws.max_row + 1
    if fila > 2:
        for col in range(1, ws.max_column + 1):
            anterior, nueva = ws.cell(fila - 1, col), ws.cell(fila, col)
            if anterior.has_style:
                nueva._style = copy(anterior._style)
    return fila


def preparar_producto(maestro_bytes, carrito_path, base, codigo, minima, tipo, peso,
                      nombres, presentaciones=None, grupo=''):
    """Devuelve Excel y vista previa; no escribe archivos ni datos remotos."""
    base = motor.normalize(base)
    codigo = codigo_limpio(codigo)
    if not base or base in {'nan', 'none'}:
        raise ValueError('Falta el nombre del producto base.')
    if not positivo(minima) or float(minima) != int(float(minima)):
        raise ValueError('La equivalencia de compra debe ser un entero mayor que cero.')
    if tipo not in TIPOS or not positivo(peso):
        raise ValueError('Elegí el tipo de producto e informá el peso del bulto en kg.')
    matches = [r for r in catalogo_carrito(carrito_path) if r['codigo'] == codigo]
    if len(matches) != 1:
        raise ValueError('El código debe aparecer una sola vez en el Carrito. Actualizá o revisá el archivo.')
    articulo = matches[0]
    if not positivo(articulo['precio']) or not articulo['descripcion']:
        raise ValueError('El artículo del Carrito debe tener descripción y precio válidos.')
    if base in motor.load_exclusiones(BytesIO(maestro_bytes)):
        raise ValueError('El producto está excluido en el Maestro. Revisá la exclusión antes de editarlo.')
    wb = load_workbook(BytesIO(maestro_bytes))
    ws = wb['Productos']
    cols = _cabeceras(ws)
    filas = [i for i in range(2, ws.max_row + 1)
             if motor.normalize(ws.cell(i, cols['producto base']).value or '') == base]
    if len(filas) > 1:
        raise ValueError('Hay productos base duplicados en el Maestro. Corregilos antes de guardar.')
    es_nuevo = not filas
    fila = filas[0] if filas else _fila_nueva(ws)
    if not es_nuevo:
        activo = ws.cell(fila, cols['activo']).value if 'activo' in cols else 'Sí'
        excluir = ws.cell(fila, cols['excluir']).value if 'excluir' in cols else 'No'
        if not motor.truthy(activo) or motor.truthy(excluir):
            raise ValueError('El producto está inactivo o excluido. No se reactivará desde este panel.')
    # Un mismo código vinculado a dos bases puede duplicar pedidos y conversiones.
    for i in range(2, ws.max_row + 1):
        if i != fila and motor.normalizar_codigo_compra(ws.cell(i, cols['codigo compra']).value) == codigo:
            raise ValueError('Ese código ya está vinculado a otro producto base. Revisá los alias en Administración.')
    for campo in ['Tipo Producto', 'Peso Compra (kg)']:
        clave = motor.normalize(campo)
        if clave not in cols:
            col = ws.max_column + 1
            ws.cell(1, col, campo)
            cols[clave] = col
    antes = {c: ws.cell(fila, cols[c]).value for c in
             ['codigo compra', 'producto compra', 'compra minima', 'tipo producto', 'peso compra kg']}
    valores = {'producto base': base, 'codigo compra': codigo,
               'producto compra': articulo['descripcion'], 'compra minima': int(minima),
               'tipo producto': tipo, 'peso compra kg': float(peso)}
    for campo, valor in valores.items():
        ws.cell(fila, cols[campo], valor)
    ws.cell(fila, cols['codigo compra']).number_format = '@'
    if es_nuevo:
        for campo, valor in [('activo', 'Sí'), ('excluir', 'No')]:
            if campo in cols:
                ws.cell(fila, cols[campo], valor)
    alias = wb['Aliases']
    ac = _cabeceras(alias)
    nombre_col = next(ac[c] for c in ['alias detectado', 'alias', 'nombre original'] if c in ac)
    presentaciones = presentaciones or {}
    conversiones = []
    for nombre in sorted(set(nombres)):
        existentes = [i for i in range(2, alias.max_row + 1)
                      if motor.normalize(alias.cell(i, nombre_col).value or '') == motor.normalize(nombre)]
        if existentes:
            if any(motor.normalize(alias.cell(i, ac['producto base']).value or '') != base for i in existentes):
                raise ValueError(f'El alias {nombre} ya está vinculado a otro producto.')
            reglas = {motor.convert_quantity(nombre, base, 1,
                        alias.cell(i, ac['tipo presentacion']).value,
                        alias.cell(i, ac['pack detectado']).value,
                        {base: {'Compra Mínima': int(minima), 'Tipo Producto': tipo}})[1]
                      for i in existentes}
            if len(reglas) != 1:
                raise ValueError(f'El alias {nombre} tiene conversiones contradictorias. Revisalo en Administración.')
            # El Maestro puede repetir el mismo alias para Stock y Ventas.
            # Conservar todas esas filas cuando su base y conversión coinciden.
            af = existentes[-1]
            presentacion = alias.cell(af, ac['tipo presentacion']).value
            pack = alias.cell(af, ac['pack detectado']).value
        else:
            if nombre not in presentaciones:
                raise ValueError(f'Confirmá la presentación del nombre: {nombre}.')
            presentacion, pack = presentaciones[nombre]
            if presentacion not in ['Presentación base', 'Unidad', 'Caja/pack x20']:
                raise ValueError('Presentación no reconocida.')
            if presentacion == 'Unidad' and not positivo(pack):
                raise ValueError('Informá cuántas unidades forman una presentación base.')
            af = _fila_nueva(alias)
            alias.cell(af, nombre_col, nombre)
            alias.cell(af, ac['producto base'], base)
            alias.cell(af, ac['tipo presentacion'], presentacion)
            alias.cell(af, ac['pack detectado'], pack)
            for campo, valor in [('origen', 'Stock'), ('grupo', grupo), ('estado', 'OK')]:
                if campo in ac:
                    alias.cell(af, ac[campo], valor)
        _, regla = motor.convert_quantity(nombre, base, 1, presentacion, pack,
                                         {base: {'Compra Mínima': int(minima), 'Tipo Producto': tipo}})
        if not existentes:
            esperado = {'Presentación base': 'cantidad', 'Caja/pack x20': 'cantidad * 2',
                        'Unidad': f'cantidad / {float(pack or 1):g}' if float(pack or 1) != 1 else 'cantidad'}[presentacion]
            if regla != esperado:
                raise ValueError(f'La presentación elegida para {nombre} no coincide con la conversión del motor ({regla}). Revisá el tipo y las unidades; los palitos usan base x10.')
        if not existentes and 'regla conversion' in ac:
            alias.cell(af, ac['regla conversion'], regla)
        conversiones.append({'Nombre en stock': nombre, 'Conversión a presentación base': regla,
                             'Alias': 'Conservado' if existentes else 'Nuevo'})
    salida = BytesIO()
    wb.save(salida)
    contenido = salida.getvalue()
    ok, errores, _ = validar_maestro(BytesIO(contenido))
    if not ok:
        raise ValueError('El Maestro resultante no pasó validación: ' + ' · '.join(errores))
    return contenido, {'nuevo': es_nuevo, 'antes': antes, 'despues': valores,
                       'articulo': articulo, 'conversiones': conversiones}


def guardar_producto(github, maestro_original, carrito_original, candidato):
    """Compara versiones y usa SHA de GitHub para evitar sobrescribir cambios simultáneos."""
    actual = github.download_file_bytes(MAESTRO)
    carrito = github.download_file_bytes(CARRITO)
    if not actual.get('ok') or not carrito.get('ok'):
        raise ValueError('No pude comprobar los archivos vigentes. No se guardó ningún cambio.')
    if actual['content_bytes'] != maestro_original or carrito['content_bytes'] != carrito_original:
        raise ValueError('El Maestro o el Carrito cambió. Volvé a abrir el panel y revisar la propuesta.')
    if not actual.get('sha'):
        raise ValueError('No pude verificar la versión del Maestro. No se guardó ningún cambio.')
    resultado = github.upload_bytes_file(path=MAESTRO, content_bytes=candidato,
                                        commit_message='Labs: completar producto desde Stock y cámara',
                                        expected_sha=actual['sha'])
    if not resultado.get('ok'):
        raise ValueError(resultado.get('message', 'No se pudo guardar el Maestro.'))
    return resultado
