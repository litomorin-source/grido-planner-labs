"""AppTest: recuperar Delicia conservando Carrito nuevo y Maestro del usuario."""
import os
import sys
from pathlib import Path
from io import BytesIO
from streamlit.testing.v1 import AppTest
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.catalogo import leer, resolver, RUTA, HOJA
from ui.home import ADMIN_PIN, generar_carrito_importacion
import motor

carrito = Path(os.environ['GRIDO_CARRITO_NUEVO']).read_bytes()
maestro = Path(os.environ['GRIDO_MAESTRO_NUEVO']).read_bytes()
datos = Path(os.environ['GRIDO_DATOS_PRUEBA'])
app=AppTest.from_file(str(Path(__file__).with_name('app_interfaz_local.py')),default_timeout=30)
app.session_state['_archivos_prueba']={RUTA:carrito,'data/Maestro_Productos_Grido.xlsx':maestro}
app.session_state['_permitir_guardado_prueba']=True
nombre='Stock_20261116_124624.csv'
app.session_state['archivos_operativos_260']={'stock':dict(bytes=(datos/nombre).read_bytes(),nombre=nombre,hash='local',descripcion='Stock')}
app.run()
assert not app.exception, [e.message for e in app.exception]
app.radio(key='modo_labs').set_value('Administrador').run()
next(t for t in app.text_input if t.label=='PIN de administrador').set_value(ADMIN_PIN).run()
assert not app.exception, [e.message for e in app.exception]
app.radio(key='accion_carrito_290').set_value('Recuperar datos de un Carrito anterior').run()
app.checkbox(key='usar_respaldo_290').set_value(True).run()
assert not app.exception, [e.message for e in app.exception]
assert next(b for b in app.button if b.label=='Guardar respaldo histórico').disabled
next(c for c in app.checkbox if c.label=='Revisé el archivo, la fecha y los cambios mostrados').set_value(True).run()
next(b for b in app.button if b.label=='Guardar respaldo histórico').click().run()
assert not app.exception, [e.message for e in app.exception]
guardado=app.session_state['_archivos_prueba'][RUTA]
assert leer(guardado)[0]==leer(carrito)[0]
assert resolver(guardado)['4000593']['precio']==13145.26
assert app.session_state['_archivos_prueba']['data/Maestro_Productos_Grido.xlsx']==maestro
app.button(key='volver_planificacion_labs').click().run()
app.radio(key='navegacion_labs').set_value('Stock y cámara').run()
assert not app.exception, [e.message for e in app.exception]
assert any('Conservan su asociación' in w.value for w in app.warning)
next(s for s in app.selectbox if s.label=='Producto a completar') if any(s.label=='Producto a completar' for s in app.selectbox) else None
assert not any(s.label=='Producto a completar' and 'barra delicia chocolate y mani' in s.options for s in app.selectbox)
app.checkbox(key='revisar_asociaciones_historicas_290').set_value(True).run()
assert not app.exception, [e.message for e in app.exception]
assert 'barra delicia chocolate y mani' in next(s for s in app.selectbox if s.label=='Producto a completar').options
# El archivo para importar una compra conserva exclusivamente las hojas del proveedor.
import pandas as pd
pedido=pd.DataFrame([{'Código Compra':'4000857','Packs a Comprar':2}])
b,_,_=generar_carrito_importacion(pedido,BytesIO(guardado))
wb=load_workbook(BytesIO(b))
assert HOJA not in wb.sheetnames
assert wb.worksheets[0].max_row==2
print('OK: recuperación de Delicia desde interfaz, confirmación, guardado en memoria, stock y exportación sin metadatos.')
