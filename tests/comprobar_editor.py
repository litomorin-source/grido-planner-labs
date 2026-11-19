from streamlit.testing.v1 import AppTest
from pathlib import Path
import sys
import os
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r))
from ui.home import ADMIN_PIN
app=AppTest.from_file(str(r/'tests/app_interfaz_local.py'),default_timeout=45)
app.session_state['_permitir_guardado_prueba']=True
app.session_state['archivos_operativos_260']={}
for k,n,folder in [('stock','Stock_20261116_124624.csv',os.environ['GRIDO_DATOS_PRUEBA']),('sabores','Cajas por Sabor (43).xlsx',os.environ['GRIDO_DATOS_PRUEBA']),('data','Kilos y Cantidades por Período (10).xlsx',os.environ['GRIDO_DATOS_PRUEBA'])]:
 app.session_state['archivos_operativos_260'][k]=dict(bytes=(Path(folder)/n).read_bytes(),nombre=n,hash='test',descripcion=k)
app.run();assert not app.exception,[e.message for e in app.exception]
app.radio(key='navegacion_labs').set_value('Stock y cámara').run();assert not app.exception,[e.message for e in app.exception]
app.checkbox(key='revisar_equivalencias_300').set_value(True).run();assert not app.exception
next(s for s in app.selectbox if s.label=='Producto a completar').set_value('bombon crocante').run()
a=next(s for s in app.selectbox if s.label=='Artículo del Carrito');a.select_index(0).run();assert not app.exception,[e.message for e in app.exception]
print('FIELDS',[(n.label,n.value) for n in app.number_input])
assert next(n for n in app.number_input if n.label=='Unidades por presentación base').value==8
next(t for t in app.text_input if t.label=='PIN de administrador para guardar').set_value(ADMIN_PIN).run()
next(b for b in app.button if b.label=='Guardar producto en el Maestro').click().run();assert not app.exception,[e.message for e in app.exception]
assert app.session_state['_archivos_prueba']['data/Maestro_Productos_Grido.xlsx']
app.radio(key='modo_labs').set_value('Administrador').run();next(t for t in app.text_input if t.label=='PIN de administrador').set_value(ADMIN_PIN).run();assert not app.exception
assert not any(c.key=='usar_respaldo_290' for c in app.checkbox)
print('OK UI cámara, revisión de producto, preview, guardado con SHA en memoria y administración.')
