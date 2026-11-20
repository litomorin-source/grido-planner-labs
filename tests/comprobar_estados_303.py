from pathlib import Path
from io import BytesIO
import hashlib, os
import pandas as pd
from streamlit.testing.v1 import AppTest
from core.estados_productos import leer_estados
from ui.home import leer_omisiones_pedido
appfile=str(Path(__file__).with_name('app_interfaz_local.py'))
a=AppTest.from_file(appfile,default_timeout=50).run()
def check(app):assert not app.exception,[e.message for e in app.exception]
check(a)
datos=Path(os.environ['GRIDO_DATOS_PRUEBA'])
a.session_state['archivos_operativos_260']={k:dict(bytes=(datos/n).read_bytes(),nombre=n,hash=hashlib.sha256((datos/n).read_bytes()).hexdigest(),descripcion='Prueba') for k,n in [('stock','Stock_20261116_124624.csv'),('sabores','Cajas por Sabor (43).xlsx'),('data','Kilos y Cantidades por Período (10).xlsx')]}
a.session_state['_permitir_guardado_prueba']=True
a.session_state['_archivos_prueba']={'data/Omisiones_Futuros_Pedidos.csv':b'producto_base,fecha,motivo\nbombon crocante,,viejo\nvela prueba,,viejo\nprueba tres,,viejo\n'}
a.run();check(a)
next(b for b in a.button if b.label=='Generar pedido').click().run();check(a)
a.multiselect(key='estados_productos').set_value(['bombon crocante']).run()
a.selectbox(key='estado_nuevo').set_value('Discontinuado').run()
a.button(key='guardar_estados').click().run();check(a)
assert 'pedido_descargas_labs' not in a.session_state
assert 'vela prueba' in a.multiselect(key='estados_productos').options
assert not a.multiselect(key='estados_productos').value
# Dos cambios más sin volver a generar.
a.multiselect(key='estados_productos').set_value(['vela prueba','prueba tres']).run()
a.selectbox(key='estado_nuevo').set_value('Excluido').run()
a.button(key='guardar_estados').click().run();check(a)
saved=dict(a.session_state['_archivos_prueba'])
estados,_=leer_estados(BytesIO(saved['data/Maestro_Productos_Grido.xlsx']))
assert estados['bombon crocante']=='Discontinuado'
assert estados['vela prueba']=='Excluido'
assert saved['data/Omisiones_Futuros_Pedidos.csv']==b'producto_base,fecha,motivo\nbombon crocante,,viejo\nvela prueba,,viejo\nprueba tres,,viejo\n'
assert not any('Revisión inicial' in w.value for w in a.warning)
# Reabrir: lee el estado persistido, no revive la omisión vieja.
b=AppTest.from_file(appfile,default_timeout=50)
b.session_state['_archivos_prueba']=saved
b.session_state['archivos_operativos_260']=a.session_state['archivos_operativos_260']
b.run();check(b)
next(btn for btn in b.button if btn.label=='Generar pedido').click().run();check(b)
p=b.session_state['pedido_descargas_labs']['result']['pedido'].set_index('Producto')
assert p.loc['bombon crocante','Packs a Comprar']==0
assert not any('Revisión inicial' in w.value for w in b.warning)
b.radio(key='navegacion_labs').set_value('Costos').run();check(b)
b.button(key='costos_mix_240').click().run();check(b)
assert not any('Productos omitidos también' in e.label for e in b.expander)
assert any('DETALLE DE COSTOS (EXCEL)' in x.label for x in b.get('download_button'))
print('OK: revisión inicial, cambios múltiples y sucesivos, invalidación, persistencia y Excel de costos.')
