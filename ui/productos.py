"""Asistente para completar datos del Maestro desde Stock y cámara."""
import hashlib
import pandas as pd
import streamlit as st
import motor
from core.alta_productos import (TIPOS, catalogo_carrito, pendientes_stock,
                                ordenar_candidatos, preparar_producto, guardar_producto, positivo)


def render_completar_productos(github, stock_path, maestro_path, carrito_path, admin_pin):
    try:
        pendientes = pendientes_stock(stock_path, maestro_path, carrito_path)
        catalogo = catalogo_carrito(carrito_path)
    except Exception as exc:
        st.warning(f'No pude revisar los datos pendientes del Maestro: {exc}')
        return
    with st.expander(f'Completar productos del stock · {len(pendientes)} pendientes', expanded=False):
        revisar_historicos = st.checkbox('También quiero revisar asociaciones con costo histórico', key='revisar_asociaciones_historicas_290')
        revisar_todos = st.checkbox('Revisar equivalencias de un producto existente', key='revisar_equivalencias_300')
        if revisar_historicos or revisar_todos:
            pendientes = pendientes_stock(stock_path, maestro_path, carrito_path, incluir_historicos=revisar_historicos, revisar_todos=revisar_todos)
            st.caption('Estas asociaciones se conservan y no requieren cambios por estar ausentes del Carrito. Revisalas solo si identificaste un código de reemplazo real.')
        if not pendientes:
            st.success('Los productos detectados tienen ficha, código de compra y costo conocido, actual o histórico.')
            return
        st.caption('Vinculá cada producto con su artículo del Carrito. El precio se seguirá leyendo del Carrito; el costo del stock se calcula con la equivalencia que confirmes.')
        st.dataframe(pd.DataFrame([{'Producto': p['producto'], 'Código actual': p['codigo'],
                                    'Pendiente': p['motivo']} for p in pendientes]),
                     hide_index=True, use_container_width=True)
        maestro_bytes, carrito_bytes = maestro_path.read_bytes(), carrito_path.read_bytes()
        version = hashlib.sha256(maestro_bytes + carrito_bytes + stock_path.read_bytes()).hexdigest()[:16]
        nombres = [p['producto'] for p in pendientes]
        elegido = st.selectbox('Producto a completar', nombres, index=None,
                              placeholder='Elegí un producto pendiente', key=f'alta_producto_{version}')
        if elegido is None:
            return
        pendiente = next(p for p in pendientes if p['producto'] == elegido)
        prefijo = 'alta_' + version + '_' + hashlib.sha256(elegido.encode()).hexdigest()[:12]
        candidatos = ordenar_candidatos(elegido, catalogo)
        etiquetas = [f"{a['codigo']} · {a['descripcion']}" for a in candidatos]
        seleccion = st.selectbox('Artículo del Carrito', range(len(candidatos)),
                                 format_func=lambda i: etiquetas[i], index=None,
                                 placeholder='Buscá por nombre o código', key=prefijo+'_articulo')
        st.caption('Las opciones se ordenan por parecido del nombre. Revisá sabor, marca y presentación antes de elegir. Si no está, actualizá el Carrito desde Administración → Actualizar archivos.')
        if seleccion is None:
            return
        articulo = candidatos[seleccion]
        precio = articulo['precio']
        st.write(f"**Artículo elegido:** {articulo['descripcion']} · Código {articulo['codigo']}")
        if not positivo(precio):
            st.warning('Este artículo no tiene precio válido. Actualizá el Carrito antes de vincularlo.')
            return
        precio_visible = f"{precio:,.2f}".replace(',', '#').replace('.', ',').replace('#', '.')
        st.write(f'**Precio del bulto en el Carrito:** $ {precio_visible}')
        st.caption('La compra mínima y el múltiplo del Carrito son restricciones de compra. No indican cuántas presentaciones contiene el bulto.')
        minima_actual = int(pendiente['minima']) if positivo(pendiente['minima']) else 0
        # Cambiar de artículo exige volver a revisar sus datos particulares.
        campos = prefijo + '_' + str(seleccion)
        tipo_actual = pendiente['tipo'] if pendiente['tipo'] in TIPOS else None
        tipo = st.selectbox('Tipo de producto', TIPOS,
                            index=TIPOS.index(tipo_actual) if tipo_actual else None,
                            placeholder='Elegí el tipo', key=campos+'_tipo')
        minima = st.number_input('Presentaciones base por bulto de compra', min_value=0,
                                 value=minima_actual, step=1, key=campos+'_minima',
                                 help='Ejemplo: 10 cajas x10 en un pack de compra = 10 presentaciones base. Para un sabor vendido por caja: 1. Revisá el valor al cambiar de código.')
        unidades_actuales = pendiente.get('unidades_base')
        unidades_base = st.number_input('Unidades por presentación base', min_value=0,
            value=int(unidades_actuales) if positivo(unidades_actuales) else 0, step=1,
            key=campos+'_unidades_base',
            help='Crocante: base = caja de 8; alfajor: caja de 6; palitos: caja de 10. Si la base es un pote, tacho o envase individual: 1. Revisá la descripción del Carrito y confirmá el contenido.')
        if minima and unidades_base:
            st.caption(f'1 bulto = {minima} presentaciones base × {unidades_base} unidades = {minima * unidades_base} unidades.')
        peso = st.number_input('Peso neto del bulto de compra (kg)', min_value=0.0,
                               value=float(articulo['peso']) if positivo(articulo['peso']) else 0.0,
                               step=0.01, format='%.3f', key=campos+'_peso',
                               help='Se propone el Peso del Carrito. Confirmá que corresponda al bulto completo, no a una unidad suelta.')
        aliases = motor.load_aliases(maestro_path)
        conocidos = set(aliases['Alias Normalizado'])
        presentaciones = {}
        for i, nombre in enumerate(pendiente['nombres']):
            existente = aliases[aliases['Alias Normalizado'].eq(motor.normalize(nombre))]
            tipo_alias = motor.normalize(existente.iloc[0]['Tipo Presentación']) if not existente.empty else ''
            opciones = ['Presentación base', 'Unidad', 'Caja/pack']
            inicial = 1 if 'unidad' in tipo_alias else 2 if ('caja' in tipo_alias or 'pack' in tipo_alias) else 0 if tipo_alias else None
            st.markdown(f'**Nombre en Stock:** {nombre}')
            pres = st.selectbox('Cómo está expresada la cantidad del stock',
                                opciones, index=inicial,
                                key=campos+f'_pres_{i}', placeholder='Confirmá la presentación',
                                help='Elegí Unidad para unidades sueltas, Caja/pack para una caja con contenido explícito, o Presentación base si la cantidad ya está expresada en la base confirmada arriba.')
            pack = None
            if pres == 'Caja/pack':
                pack = st.number_input('Unidades contenidas en esta caja', min_value=1,
                                       value=int(existente.iloc[0]['Pack Detectado']) if not existente.empty and positivo(existente.iloc[0]['Pack Detectado']) else 1, step=1, key=campos+f'_pack_{i}')
            if pres:
                presentaciones[nombre] = (pres, pack)
        # Construir siempre la vista previa desde los campos visibles; evita guardar
        # una propuesta vieja después de modificar el producto o su equivalencia.
        try:
            candidato, vista = preparar_producto(maestro_bytes, carrito_path, elegido,
                                                articulo['codigo'], minima, tipo, peso,
                                                pendiente['nombres'], presentaciones, pendiente['grupo'], unidades_base=unidades_base)
        except ValueError as exc:
            st.info(str(exc))
            return
        st.markdown('#### Revisar antes de guardar')
        etiquetas_campos = {'codigo compra': 'Código de compra', 'producto compra': 'Descripción de compra',
                           'compra minima': 'Presentaciones por bulto', 'tipo producto': 'Tipo de producto',
                           'peso compra kg': 'Peso del bulto (kg)',
                           'unidades por presentacion base': 'Unidades por presentación base'}
        cambios = pd.DataFrame([{'Dato': label,
                                 'Actual': str(vista['antes'].get(campo) or '—'),
                                 'Propuesto': str(vista['despues'][campo])}
                                for campo, label in etiquetas_campos.items()])
        st.dataframe(cambios, hide_index=True, use_container_width=True)
        st.dataframe(pd.DataFrame(vista['conversiones']), hide_index=True, use_container_width=True)
        st.caption('El guardado agrega o actualiza esta ficha y los nombres nuevos del stock. Conserva las demás hojas, omisiones e historial. Luego se deben regenerar los informes.')
        pin = st.text_input('PIN de administrador para guardar', type='password', key=campos+'_pin')
        if st.button('Guardar producto en el Maestro', type='primary', key=campos+'_guardar',
                     disabled=pin != admin_pin):
            try:
                guardar_producto(github, maestro_bytes, carrito_bytes, candidato)
            except Exception as exc:
                st.error(f'No se guardó el producto: {exc}')
                return
            for clave in ['pedido_descargas_labs', 'ultimo_analisis_snapshot', 'costos_mix_actual',
                          'informe_stock_bytes_260', 'historial_maestro', 'data_status']:
                st.session_state.pop(clave, None)
            st.session_state['mensaje_alta_producto'] = f'{elegido}: Maestro actualizado. Regenerá el informe de Stock, el Pedido y los Costos para usar los nuevos datos.'
            st.rerun()
