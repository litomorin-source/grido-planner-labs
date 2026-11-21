"""Regresión de estados: UI simplificada 3.0.4, sin escrituras remotas."""
from pathlib import Path
from io import BytesIO
import hashlib, os
import pandas as pd
from streamlit.testing.v1 import AppTest
from core.estados_productos import leer_estados
appfile=str(Path(__file__).with_name('app_interfaz_local.py'))
a=AppTest.from_file(appfile,default_timeout=50).run()
def check(app):assert not app.exception,[e.message for e in app.exception]
check(a)
datos=Path(os.environ['GRIDO_DATOS_PRUEBA'])
a.session_state['archivos_operativos_260']={k:dict(bytes=(datos/n).read_bytes(),nombre=n,hash=hashlib.sha256((datos/n).read_bytes()).hexdigest(),descripcion='Prueba') for k,n in [('stock','Stock_20261116_124624.csv'),('sabores','Cajas por Sabor (43).xlsx'),('data','Kilos y Cantidades por Período (10).xlsx')]}
a.session_state['_permitir_guardado_prueba']=True
anterior=b'producto_base,fecha,motivo\nvela antigua,,viejo\n'
a.session_state['_archivos_prueba']={'data/Omisiones_Futuros_Pedidos.csv':anterior}
a.run();check(a)
next(b for b in a.button if b.label=='Generar pedido').click().run();check(a)
assert not any(s.key in ('estado_nuevo','estados_productos') for s in list(a.selectbox)+list(a.multiselect))
assert not any('Revisión inicial' in w.value for w in a.warning)
a.session_state['omision_candidatos']=pd.DataFrame({'Producto':['vela antigua','torta con oreo','vela nueva','prueba dos','prueba tres']})
a.run();check(a)
assert a.multiselect(key='sugerencias_excluir').options==['prueba dos','prueba tres','vela nueva']
assert 'data/Maestro_Productos_Grido.xlsx' not in a.session_state['_archivos_prueba']
consulta=next(e for e in a.expander if e.label.startswith('Consultar productos excluidos'))
assert not consulta.proto.expanded
# Dos exclusiones juntas, después una tercera, sin regenerar.
a.multiselect(key='sugerencias_excluir').set_value(['vela nueva','prueba dos']).run()
a.button(key='excluir_sugerencias').click().run();check(a)
assert 'pedido_descargas_labs' not in a.session_state
assert a.multiselect(key='sugerencias_excluir').options==['prueba tres']
a.multiselect(key='sugerencias_excluir').set_value(['prueba tres']).run()
a.button(key='excluir_sugerencias').click().run();check(a)
assert not any(s.key=='sugerencias_excluir' for s in a.multiselect)
saved=dict(a.session_state['_archivos_prueba'])
assert saved['data/Omisiones_Futuros_Pedidos.csv']==anterior
estados,_=leer_estados(BytesIO(saved['data/Maestro_Productos_Grido.xlsx']))
assert estados['vela nueva']=='Excluido'
assert estados['torta con oreo']=='Excluido'
# Nueva sesión conserva decisiones y no vuelve a sugerir excluidos.
b=AppTest.from_file(appfile,default_timeout=50)
b.session_state['_archivos_prueba']=saved
b.session_state['archivos_operativos_260']=a.session_state['archivos_operativos_260']
b.run();check(b)
next(btn for btn in b.button if btn.label=='Generar pedido').click().run();check(b)
b.session_state['omision_candidatos']=pd.DataFrame({'Producto':['vela nueva','vela antigua','prueba tres']})
b.run();check(b)
assert not any(s.key=='sugerencias_excluir' for s in b.multiselect)
b.radio(key='navegacion_labs').set_value('Costos').run();check(b)
b.button(key='costos_mix_240').click().run();check(b)
assert any('DETALLE DE COSTOS (EXCEL)' in x.label for x in b.get('download_button'))
print('OK: solo sugerencias nuevas, consulta contraída, omisiones preservadas, múltiples exclusiones, persistencia y Excel.')
