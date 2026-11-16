"""AppTest del guardado. El adaptador escribe solo en memoria, nunca en GitHub."""
import os
from pathlib import Path
from io import BytesIO
import sys
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import motor
from ui.home import ADMIN_PIN
from core.alta_productos import MAESTRO

app = AppTest.from_file(str(Path(__file__).with_name('app_interfaz_local.py')), default_timeout=30)
datos = Path(os.environ['GRIDO_DATOS_PRUEBA'])
nombre = 'Stock_20261116_124624.csv'
app.session_state['archivos_operativos_260'] = {
    'stock': dict(bytes=(datos/nombre).read_bytes(), nombre=nombre, hash='prueba', descripcion='Stock')}
app.session_state['_permitir_guardado_prueba'] = True
app.run()
app.radio(key='navegacion_labs').set_value('Stock y cámara').run()
assert not app.exception, [e.message for e in app.exception]
next(s for s in app.selectbox if s.label == 'Producto a completar').set_value('palito frutal limon').run()
next(s for s in app.selectbox if s.label == 'Artículo del Carrito').set_value(0).run()
assert not app.exception, [e.message for e in app.exception]
assert any('4000857' in m.value for m in app.markdown)
next(n for n in app.number_input if n.label == 'Presentaciones base por bulto de compra').set_value(10).run()
guardar = lambda: next(b for b in app.button if b.label == 'Guardar producto en el Maestro')
assert guardar().disabled
next(t for t in app.text_input if t.label == 'PIN de administrador para guardar').set_value(ADMIN_PIN).run()
assert not guardar().disabled
guardar().click().run()
assert not app.exception, [e.message for e in app.exception]
contenido = app.session_state['_archivos_prueba'][MAESTRO]
p = motor.load_productos(BytesIO(contenido)).set_index('Producto Base').loc['palito frutal limon']
assert motor.normalizar_codigo_compra(p['Código Compra']) == '4000857' and p['Compra Mínima'] == 10
assert next(s for s in app.selectbox if s.label == 'Producto a completar').options == ['crema al cielo']
assert any('Maestro actualizado' in e.value for e in app.success)
assert 'pedido_descargas_labs' not in app.session_state
print('OK: selección, vista previa, PIN, guardado en memoria, recarga y resolución del pendiente.')
