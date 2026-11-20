"""Carrito vigente e historial de referencias, guardados en un único Excel.

La primera hoja conserva el formato del proveedor. La hoja interna se elimina
de las exportaciones para importar pedidos. No modifica el Maestro ni el stock.
"""
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import hashlib
import json
import math
import re
import unicodedata
from openpyxl import load_workbook

HOJA = '_GP_Historial'
from core.rutas import CARRITO as RUTA
CAMPOS = {'descripcion': 'Descripcion', 'precio': 'precio', 'cubicaje': 'Cubicaje',
          'peso': 'Peso', 'disponible': 'Disponible', 'maximo': 'maximo',
          'minimo': 'minimo', 'multiplo': 'multiplo', 'iva': 'impuestoIva',
          'deposito': 'Deposito', 'grupo': 'GrupoProducto'}


def normalizar(v):
    s = ''.join(c for c in unicodedata.normalize('NFD', str(v or '').lower())
                if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', s)).strip()


def codigo(v):
    if v is None or str(v).strip().lower() in {'', 'nan', 'none', '<na>'}:
        return ''
    s = str(v).strip()
    return s[:-2] if s.endswith('.0') and s[:-2].isdigit() else s


def numero(v):
    if v is None or str(v).strip() in {'', '-'}:
        return None
    s = str(v).strip().replace('$', '').replace(' ', '')
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        n = float(s)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def valido(v):
    return v is not None and math.isfinite(float(v)) and float(v) > 0


def contenido(origen):
    if isinstance(origen, bytes):
        return origen
    if hasattr(origen, 'getvalue'):
        return origen.getvalue()
    return Path(origen).read_bytes()


def leer(origen):
    wb = load_workbook(BytesIO(contenido(origen)), data_only=True)
    ws = wb.worksheets[0]
    columnas = {normalizar(c.value): c.column - 1 for c in ws[1] if c.value is not None}
    requeridas = ['codigo', 'descripcion', 'precio', 'peso', 'cubicaje']
    if any(c not in columnas for c in requeridas):
        raise ValueError('El Carrito no contiene código, descripción, precio, peso y cubicaje.')
    actuales = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        cod = codigo(row[columnas['codigo']])
        if not cod:
            continue
        if cod in actuales:
            raise ValueError(f'Código repetido en el Carrito: {cod}. Revisá las filas o depósitos antes de cargarlo.')
        r = {'codigo': cod}
        for campo, nombre in CAMPOS.items():
            i = columnas.get(normalizar(nombre))
            v = row[i] if i is not None and i < len(row) else None
            r[campo] = str(v or '').strip() if campo in {'descripcion', 'deposito', 'grupo'} else numero(v)
        if not r['descripcion']:
            raise ValueError(f'El código {cod} no tiene descripción.')
        actuales[cod] = r
    if not actuales:
        raise ValueError('El Carrito no tiene artículos.')
    historial, bloqueos = [], {}
    if HOJA in wb.sheetnames:
        ws = wb[HOJA]
        if ws.cell(1, 1).value != 'GridoPlanner catálogo v1':
            raise ValueError('El historial del Carrito tiene un formato desconocido. No se reemplazó.')
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]:
                continue
            try:
                r = json.loads(row[0])
                if r['tipo_registro'] == 'dato':
                    if not r.get('codigo') or not r.get('evento'):
                        raise ValueError('Dato sin código o evento')
                    historial.append(r)
                elif r['tipo_registro'] == 'bloqueo':
                    bloqueos[r['codigo']] = r['referencia']
                else:
                    raise ValueError('Registro desconocido')
            except (KeyError, TypeError, json.JSONDecodeError, ValueError) as exc:
                raise ValueError('No se pudo leer el historial del Carrito. Conservá el archivo y revisalo.') from exc
    wb.close()
    return actuales, historial, bloqueos


def _evento(actuales):
    return hashlib.sha256(json.dumps(actuales, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _registrar(actuales, nombre, fecha=None):
    evento = _evento(actuales)
    ahora = datetime.now(timezone.utc).isoformat(timespec='seconds')
    return [dict(r, tipo_registro='dato', evento=evento, archivo=nombre,
                 fecha=str(fecha) if fecha else '', registrado=ahora) for r in actuales.values()]


def _con_vigente(actuales, historial):
    if not any(r.get('evento') == _evento(actuales) for r in historial):
        return historial + _registrar(actuales, 'Carrito vigente previo (fecha de origen no informada)')
    return list(historial)


def compatible(a, b):
    for c in ['peso', 'cubicaje']:
        if valido(a.get(c)) and valido(b.get(c)) and not math.isclose(a[c], b[c], rel_tol=1e-6):
            return False
    return True


def resolver(origen):
    actuales, historial, bloqueos = leer(origen)
    # Los bloqueos anteriores debidos solo al nombre ya no requieren revisión.
    bloqueos = {c: r for c, r in bloqueos.items() if c not in actuales or not compatible(r, actuales[c])}
    evento_actual = _evento(actuales)
    todos = set(actuales) | {r['codigo'] for r in historial}
    salida = {}
    for cod in sorted(todos):
        anteriores = [r for r in historial if r['codigo'] == cod]
        actual = actuales.get(cod)
        referencia = bloqueos.get(cod) or actual or (anteriores[-1] if anteriores else {})
        r = dict(referencia)
        r.update(codigo=cod, presente=actual is not None, revisar=cod in bloqueos)
        fuentes = {}
        for campo in ['precio', 'peso', 'cubicaje']:
            fuente = None
            if cod not in bloqueos and actual and valido(actual.get(campo)):
                valor = actual[campo]
                fuente = next((h for h in reversed(anteriores) if h.get('evento') == evento_actual), actual)
                fuentes[campo] = 'Actual'
            else:
                candidatos = ([bloqueos[cod]] if cod in bloqueos else []) + list(reversed(anteriores))
                fuente = next((h for h in candidatos if valido(h.get(campo)) and compatible(referencia, h)), None)
                valor = fuente[campo] if fuente else None
                fuentes[campo] = 'Histórico' if fuente else 'Sin dato'
            r[campo] = valor
            r['fecha_' + campo] = fuente.get('fecha_' + campo, fuente.get('fecha', '')) if fuente else ''
            r['archivo_' + campo] = fuente.get('archivo_' + campo, fuente.get('archivo', 'Carrito actual')) if fuente else ''
        r['fuentes'] = fuentes
        if r['revisar']:
            estado = 'Cambio de presentación para revisar'
        elif not r['presente']:
            estado = 'Ausente del Carrito actual'
        elif 'Histórico' in fuentes.values():
            estado = 'Datos actuales incompletos; usa respaldo'
        elif 'Sin dato' in fuentes.values():
            estado = 'Datos pendientes sin respaldo'
        else:
            estado = 'Vigente'
        r['estado'] = estado
        r['comprable'] = bool(actual and not r['revisar'] and valido(actual.get('precio')))
        salida[cod] = r
    return salida


def comparar(anterior, nuevo):
    actuales, hist, _ = leer(anterior)
    entrantes, _, _ = leer(nuevo)
    resueltos = resolver(anterior)
    cambios = []
    for cod in sorted(set(actuales) | set(entrantes)):
        a, b = actuales.get(cod), entrantes.get(cod)
        if b is None:
            cambios.append(dict(codigo=cod, producto=a['descripcion'], cambio='Ausente', detalle='Conserva datos anteriores; no se declara discontinuado.'))
            continue
        if a is None:
            cambios.append(dict(codigo=cod, producto=b['descripcion'], cambio='Reaparece' if cod in resueltos else 'Nuevo', detalle='No cambia asociaciones del Maestro.'))
            a = resueltos.get(cod)
        if a:
            campos = [c for c in CAMPOS if a.get(c) != b.get(c)]
            if campos:
                detalle = '; '.join(f"{c}: {a.get(c)} → {b.get(c)}" for c in campos)
                cambios.append(dict(codigo=cod, producto=b['descripcion'], cambio='Datos modificados', detalle=detalle))
            if not compatible(a, b):
                cambios.append(dict(codigo=cod, producto=b['descripcion'], cambio='Presentación para revisar', detalle=f"Anterior: {a['descripcion']} / peso {a.get('peso')} / cubicaje {a.get('cubicaje')}"))
            if valido(a.get('precio')) and valido(b.get('precio')):
                variacion = (b['precio']/a['precio'] - 1)*100
                if abs(variacion) >= 20:
                    cambios.append(dict(codigo=cod, producto=b['descripcion'], cambio='Variación de precio ≥20%', detalle=f'{variacion:+.1f}%'))
        for campo in ['precio', 'peso', 'cubicaje']:
            if not valido(b.get(campo)):
                cambios.append(dict(codigo=cod, producto=b['descripcion'], cambio='Dato vacío o inválido', detalle=campo))
    return cambios


def preparar(anterior, entrante, nombre, fecha=None, historico=False, confirmar_misma_presentacion=()):
    """Carga histórica: solo aporta respaldo; nunca sustituye filas del catálogo vigente."""
    actuales, historial, bloqueos = leer(anterior)
    nuevos, _, _ = leer(entrante)
    historial = _con_vigente(actuales, historial)
    referencias = resolver(anterior)
    evento_nuevo = _evento(nuevos)
    fecha_texto = str(fecha) if fecha else ''
    nuevos_registros = [] if any(r.get('evento') == evento_nuevo and r.get('fecha', '') == fecha_texto
                                 for r in historial) else _registrar(nuevos, nombre, fecha)
    if historico:
        # Un archivo anterior solo cubre huecos. Los datos previamente conocidos
        # tienen prioridad, aun cuando no conocemos la fecha del archivo importado.
        for r in nuevos_registros:
            r['importado'] = True
        importados = nuevos_registros + [r for r in historial if r.get('importado')]
        importados.sort(key=lambda r: r.get('fecha', ''))
        historial = importados + [r for r in historial if not r.get('importado')]
        base = contenido(anterior)
    else:
        for cod, r in nuevos.items():
            anterior_r = referencias.get(cod)
            if anterior_r and not compatible(anterior_r, r):
                bloqueos.setdefault(cod, anterior_r)
            if cod in confirmar_misma_presentacion:
                bloqueos.pop(cod, None)
        historial += nuevos_registros
        base = contenido(entrante)
    wb = load_workbook(BytesIO(base))
    if HOJA in wb.sheetnames:
        del wb[HOJA]
    ws = wb.create_sheet(HOJA)
    ws.append(['GridoPlanner catálogo v1'])
    for r in historial:
        ws.append([json.dumps(r, ensure_ascii=False, allow_nan=False)])
    for cod, referencia in bloqueos.items():
        ws.append([json.dumps(dict(tipo_registro='bloqueo', codigo=cod, referencia=referencia), ensure_ascii=False, allow_nan=False)])
    ws.sheet_state = 'hidden'
    wb.active = 0
    salida = BytesIO()
    wb.save(salida)
    leer(salida.getvalue())
    return salida.getvalue()


def guardar(github, original, candidato):
    actual = github.download_file_bytes(RUTA)
    if not actual.get('ok') or not actual.get('sha'):
        raise ValueError('No pude verificar la versión actual del Carrito.')
    if actual['content_bytes'] != original:
        raise ValueError('El Carrito cambió mientras revisabas. Volvé a cargar la comparación.')
    r = github.upload_bytes_file(path=RUTA, content_bytes=candidato,
                                 commit_message='Labs: actualizar Carrito conservando referencias históricas',
                                 expected_sha=actual['sha'])
    if not r.get('ok'):
        raise ValueError(r.get('message', 'No se pudo guardar el Carrito.'))
    return r


def detalle_referencias(origen, codigos=None):
    datos = resolver(origen)
    filtro = None if codigos is None else {codigo(c) for c in codigos}
    return [{'Código': cod, 'Producto compra': r['descripcion'], 'Estado': r['estado'],
             'Precio bulto': r.get('precio'), 'Origen precio': r['fuentes']['precio'],
             'Fecha precio': r.get('fecha_precio') or 'Sin fecha informada',
             'Cubicaje': r.get('cubicaje'), 'Origen cubicaje': r['fuentes']['cubicaje'],
             'Fecha cubicaje': r.get('fecha_cubicaje') or 'Sin fecha informada',
             'Archivo de referencia': r.get('archivo_precio', '')}
            for cod, r in datos.items() if filtro is None or cod in filtro]


def ajustar_compra(cantidad, referencia):
    """Conserva la necesidad calculada; el Carrito solo aporta advertencias."""
    if cantidad <= 0:
        return cantidad, ''
    if not referencia:
        return cantidad, 'Sin referencia en Carrito; revisar código y costo'
    avisos = []
    if not referencia.get('presente', True):
        avisos.append('Ausente del Carrito; revisar disponibilidad')
    if referencia.get('revisar'):
        avisos.append('Presentación para revisar; cálculo según Maestro')
    if referencia.get('fuentes', {}).get('precio') == 'Histórico':
        avisos.append('Precio histórico de referencia')
    elif not valido(referencia.get('precio')):
        avisos.append('Precio pendiente')
    for campo, etiqueta in [('minimo', 'mínimo'), ('maximo', 'máximo'), ('disponible', 'disponibilidad')]:
        valor = referencia.get(campo)
        if valor is None:
            continue
        if valor < 0:
            avisos.append(f'{etiqueta.capitalize()} inválida en Carrito')
        elif (campo == 'minimo' and cantidad < valor) or (campo != 'minimo' and cantidad > valor):
            avisos.append(f'Carrito informa {etiqueta} {valor:g}; revisar manualmente')
    multiplo = referencia.get('multiplo')
    if multiplo is not None:
        if multiplo <= 0 or multiplo != int(multiplo):
            avisos.append('Múltiplo inválido en Carrito')
        elif cantidad % multiplo:
            avisos.append(f'Carrito informa múltiplo {multiplo:g}; revisar manualmente')
    return cantidad, ' · '.join(avisos)


def precios_compatibles(precios, referencias, productos):
    """No divide un precio histórico de una presentación por la equivalencia de otra."""
    salida = dict(precios)
    for _, p in productos.iterrows():
        cod = codigo(p.get('Código Compra'))
        r = referencias.get(cod, {})
        if r.get('fuentes', {}).get('precio') != 'Histórico':
            continue
        peso = numero(p.get('Peso Compra (kg)'))
        incompatible = (valido(peso) and valido(r.get('peso')) and not math.isclose(peso,r['peso'],rel_tol=1e-6))
        if incompatible:
            salida.pop(cod, None)
    return salida
