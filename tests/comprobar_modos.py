"""Regresión de navegación Usuario/Administrador, sin conexión externa."""
from pathlib import Path
import sys
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ui.home import ADMIN_PIN

app = AppTest.from_file(str(Path(__file__).with_name('app_interfaz_local.py')), default_timeout=30).run()
assert not app.exception
app.radio(key='navegacion_labs').set_value('Stock y cámara').run()
app.radio(key='modo_labs').set_value('Administrador').run()
assert not app.exception
assert all(r.key != 'navegacion_labs' for r in app.radio)
assert app.button(key='volver_planificacion_labs')
next(t for t in app.text_input if t.label == 'PIN de administrador').set_value(ADMIN_PIN).run()
assert not app.exception, [e.message for e in app.exception]
assert all(r.key != 'navegacion_labs' for r in app.radio)
assert any(h.value == 'Centro de Datos' for h in app.header)
app.button(key='volver_planificacion_labs').click().run()
assert not app.exception
assert app.radio(key='modo_labs').value == 'Usuario'
assert app.radio(key='navegacion_labs').value == 'Stock y cámara'
assert not any(t.label == 'PIN de administrador' for t in app.text_input)
app.radio(key='navegacion_labs').set_value('Costos').run()
app.radio(key='modo_labs').set_value('Administrador').run()
app.run()  # Permitir la limpieza de widgets de Streamlit.
app.radio(key='modo_labs').set_value('Usuario').run()
assert not app.exception
assert app.radio(key='navegacion_labs').value == 'Costos'
print('OK: menú oculto con y sin PIN, retorno por botón y selector, última sección conservada.')
