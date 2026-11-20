"""Ejecutar por separado: GRIDO_DATOS_PRUEBA=/carpeta python tests/comprobar_interfaz.py"""
import hashlib
import logging
import os
from pathlib import Path
import warnings
from streamlit.testing.v1 import AppTest

for name in logging.root.manager.loggerDict:
    if name.startswith('streamlit'):
        logging.getLogger(name).setLevel(logging.ERROR)
warnings.filterwarnings('ignore', message='Workbook contains no default style')

datos = Path(os.environ['GRIDO_DATOS_PRUEBA'])
app = AppTest.from_file(str(Path(__file__).with_name('app_interfaz_local.py')), default_timeout=30)

def verificar():
    assert not app.exception, [e.message for e in app.exception]

app.run()
verificar()
assert not any(b.label == 'Generar pedido' for b in app.button)
archivos = {}
for tipo, nombre in [('stock', 'Stock_20261116_124624.csv'),
                     ('sabores', 'Cajas por Sabor (43).xlsx'),
                     ('data', 'Kilos y Cantidades por Período (10).xlsx')]:
    contenido = (datos / nombre).read_bytes()
    archivos[tipo] = dict(bytes=contenido, nombre=nombre,
                          hash=hashlib.sha256(contenido).hexdigest(), descripcion='Prueba')
app.session_state['archivos_operativos_260'] = archivos
app.run()
verificar()
next(b for b in app.button if b.label == 'Generar pedido').click().run()
verificar()
estado = app.session_state['pedido_descargas_labs']
assert estado['result']['pedido']['Packs a Comprar'].sum() == 171
assert estado['result']['valor_pedido_total'] == 4717545
descarga = estado['pedido_bytes']
assert descarga and estado['carrito_bytes']
for pagina in ['Stock y cámara', 'Costos', 'Configuración', 'Pallets', 'Pedido']:
    app.radio(key='navegacion_labs').set_value(pagina).run()
    verificar()
    assert app.session_state['pedido_descargas_labs']['pedido_bytes'] == descarga
for metrica in ['Bultos', 'Unidades equivalentes', 'Valor del stock']:
    app.selectbox(key='historial_metrica').set_value(metrica).run()
    verificar()
next(b for b in app.button if b.label == 'CALCULAR COSTOS SEGÚN MI MIX').click().run()
verificar()
assert app.session_state['costos_mix_actual']
next(n for n in app.number_input if n.label == 'Semanas objetivo').set_value(3.0).run()
verificar()
assert 'pedido_descargas_labs' not in app.session_state
next(b for b in app.button if b.label == 'Limpiar archivos').click().run()
verificar()
assert app.session_state['archivos_operativos_260'] == {}
print('OK: carga, generación, navegación, descargas conservadas, gráficos, costos, invalidación y limpieza.')
