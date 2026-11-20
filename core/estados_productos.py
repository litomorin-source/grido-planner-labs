"""Estados del Maestro y transición explícita de las antiguas omisiones."""
from io import BytesIO
from openpyxl import load_workbook
from core.rutas import MAESTRO

ESTADOS = ('Activo', 'Discontinuado', 'Excluido')
MIGRACION = 'Omisiones externas revisadas'


def leer_estados(path):
    from motor import normalize, truthy
    wb = load_workbook(path, read_only=True, data_only=True)
    def registros(nombre):
        if nombre not in wb.sheetnames:
            return []
        rows = iter(wb[nombre].values)
        cols = [normalize(c or '') for c in next(rows, [])]
        return [dict(zip(cols, r)) for r in rows]
    aliases = {normalize(r.get('alias detectado') or r.get('alias') or ''):
               normalize(r.get('producto base') or '') for r in registros('Aliases')}
    def base(nombre):
        n = normalize(nombre or '')
        return aliases.get(n, n)
    estados, explicitos = {}, set()
    for r in registros('Productos'):
        n = base(r.get('producto base') or r.get('producto'))
        if not n:
            continue
        estados[n] = 'Activo' if truthy(r.get('activo', 'Sí')) and not truthy(r.get('excluir', 'No')) else 'Excluido'
    # Exclusiones antiguas siguen vigentes, aun si nombran un alias.
    for r in registros('Exclusiones'):
        n = base(r.get('producto') or r.get('producto opcion') or r.get('alias') or r.get('nombre') or next(iter(r.values()), None))
        if not n:
            continue
        estado = str(r.get('estado') or '').strip()
        if estado and estado not in ESTADOS:
            raise ValueError(f'Estado inválido para {n}: {estado}')
        estados[n] = estado or 'Excluido'
        if estado:
            explicitos.add(n)
    for r in registros('Productos'):
        n = base(r.get('producto base') or r.get('producto'))
        estado = str(r.get('estado') or '').strip()
        if estado:
            if estado not in ESTADOS:
                raise ValueError(f'Estado inválido para {n}: {estado}')
            estados[n] = estado
            explicitos.add(n)
    wb.close()
    return estados, explicitos


def guardar_estados(github, original, cambios, pendientes):
    """Un único guardado con SHA; no elimina datos ni escribe el CSV anterior."""
    from motor import normalize, load_aliases
    cambios = {normalize(k): v for k, v in cambios.items()}
    if not cambios or any(v not in ESTADOS for v in cambios.values()):
        raise ValueError('Seleccioná productos y un estado válido.')
    actual = github.download_file_bytes(MAESTRO)
    if not actual.get('ok') or not actual.get('sha'):
        raise ValueError('No pude verificar el Maestro. Reintentá.')
    if actual['content_bytes'] != original:
        raise ValueError('El Maestro cambió. Recargá la pantalla antes de guardar.')
    wb = load_workbook(BytesIO(original))
    aliases = load_aliases(BytesIO(original))
    amap = dict(zip(aliases['Alias Normalizado'], aliases['Producto Base']))
    def base(n):
        n = normalize(n or '')
        return amap.get(n, n)
    def columnas(ws):
        return {normalize(c.value or ''): c.column for c in ws[1]}
    productos = wb['Productos']; pc = columnas(productos)
    if 'estado' not in pc:
        pc['estado'] = productos.max_column + 1
        productos.cell(1, pc['estado'], 'Estado')
    filas = {}
    for i in range(2, productos.max_row + 1):
        n = base(productos.cell(i, pc['producto base']).value)
        if n in filas:
            raise ValueError(f'Producto duplicado en Maestro: {n}')
        filas[n] = i
    ex = wb['Exclusiones']; ec = columnas(ex)
    nombre = next((ec[k] for k in ['producto', 'producto opcion', 'alias', 'nombre'] if k in ec), 1)
    if 'estado' not in ec:
        ec['estado'] = ex.max_column + 1
        ex.cell(1, ec['estado'], 'Estado')
    # Retirar las exclusiones antiguas de los productos revisados, incluidos aliases.
    for i in range(ex.max_row, 1, -1):
        if base(ex.cell(i, nombre).value) in cambios:
            ex.delete_rows(i)
    for n, estado in cambios.items():
        if n in filas:
            i = filas[n]
            productos.cell(i, pc['estado'], estado)
            # Compatibilidad con editores anteriores: nunca son una decisión independiente.
            if 'activo' in pc:
                productos.cell(i, pc['activo'], 'No' if estado == 'Excluido' else 'Sí')
            if 'excluir' in pc:
                productos.cell(i, pc['excluir'], 'Sí' if estado == 'Excluido' else 'No')
        else:
            if estado == 'Discontinuado':
                raise ValueError(f'{n}: primero completá su ficha y equivalencias en el Maestro; también podés excluirlo del análisis.')
            i = ex.max_row + 1
            ex.cell(i, nombre, n); ex.cell(i, ec['estado'], estado)
    restantes = {base(f['producto_base']) for f in pendientes} - set(cambios)
    if not restantes:
        ws = wb['Configuración']; cols = columnas(ws)
        p, v = cols['parametro'], cols['valor']
        row = next((i for i in range(2, ws.max_row+1) if ws.cell(i,p).value == MIGRACION), ws.max_row+1)
        ws.cell(row,p,MIGRACION); ws.cell(row,v,'Sí')
    salida = BytesIO(); wb.save(salida)
    result = github.upload_bytes_file(path=MAESTRO, content_bytes=salida.getvalue(), expected_sha=actual['sha'],
                                      commit_message='Actualizar estados de productos en el Maestro')
    if not result.get('ok'):
        raise ValueError(result.get('message', 'No se pudieron guardar los estados.'))
    return result
