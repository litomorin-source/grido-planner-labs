from pathlib import Path
from io import BytesIO
import hashlib,os
import pandas as pd
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest
appfile=str(Path(__file__).with_name('app_interfaz_local.py'))
a=AppTest.from_file(appfile,default_timeout=40).run()
def check(app):assert not app.exception,[e.message for e in app.exception]
check(a)
datos=Path(os.environ['GRIDO_DATOS_PRUEBA'])
a.session_state['archivos_operativos_260']={k:dict(bytes=(datos/n).read_bytes(),nombre=n,hash=hashlib.sha256((datos/n).read_bytes()).hexdigest(),descripcion='Prueba') for k,n in [('stock','Stock_20261116_124624.csv'),('sabores','Cajas por Sabor (43).xlsx'),('data','Kilos y Cantidades por Período (10).xlsx')]}
a.run();check(a)
next(b for b in a.button if b.label=='Generar pedido').click().run();check(a)
for campo in ['pedido_bytes','carrito_bytes']:
 w=load_workbook(BytesIO(a.session_state['pedido_descargas_labs'][campo]));count=0
 for s in w:
  for row in s:
   for c in row:
    if c.value in ['Precio Pack','Precio bulto','Costo Unitario Eq','precio']:
     for rr in range(c.row+1,s.max_row+1):
      v=s.cell(rr,c.column)
      if isinstance(v.value,(int,float)):
       assert '$' in v.number_format,(campo,s.title,v.coordinate,v.number_format)
       count+=1
 assert count>0
# Tres candidatos: omitir dos juntos, luego el restante, sin generar de nuevo.
a.session_state['omision_candidatos']=pd.DataFrame({'Producto':['prueba uno','prueba dos','prueba tres']})
a.session_state['_permitir_guardado_prueba']=True
a.run();check(a)
a.multiselect(key='omision_faltantes_productos').set_value(['prueba uno','prueba dos']).run()
a.button(key='omision_faltantes_guardar').click().run();check(a)
assert a.multiselect(key='omision_faltantes_productos').options==['prueba tres']
assert 'pedido_descargas_labs' not in a.session_state
assert not a.multiselect(key='omision_faltantes_productos').value
a.multiselect(key='omision_faltantes_productos').set_value(['prueba tres']).run()
a.button(key='omision_faltantes_guardar').click().run();check(a)
assert 'prueba tres' in a.session_state['_archivos_prueba']['data/Omisiones_Futuros_Pedidos.csv'].decode('utf-8-sig')
# Capacidad guardada y una sesión enteramente nueva lee el Maestro persistido.
a.radio(key='navegacion_labs').set_value('Stock y cámara').run();check(a)
a.number_input(key='capacidad_camara_limite').set_value(1234.0).run()
a.button(key='guardar_capacidad_camara').click().run();check(a)
saved=dict(a.session_state['_archivos_prueba'])
b=AppTest.from_file(appfile,default_timeout=40)
b.session_state['_archivos_prueba']=saved
b.run();check(b)
b.radio(key='navegacion_labs').set_value('Stock y cámara').run();check(b)
assert b.number_input(key='capacidad_camara_limite').value==1234.0
print('OK: omisiones múltiples y sucesivas, descargas invalidadas, formatos monetarios, capacidad persistida tras sesión nueva.')
