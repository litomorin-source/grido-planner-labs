"""Revisión de cambios y recuperación de un Carrito anterior."""
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
from pathlib import Path
import pandas as pd
import streamlit as st
from core.catalogo import (leer, comparar, preparar, guardar, resolver,
                           detalle_referencias, RUTA)
from core.validators import validar_carrito
from io import BytesIO


def render_actualizar_carrito(github):
    st.subheader('Carrito e historial de referencias')
    mensaje = st.session_state.pop('mensaje_carrito_290', None)
    if mensaje:
        st.success(mensaje)
    actual = github.download_file_bytes(RUTA)
    if not actual.get('ok'):
        st.error('No pude descargar el Carrito vigente para compararlo. Reintentá antes de actualizar.')
        return
    original = actual['content_bytes']
    try:
        actuales, historial, bloqueos = leer(original)
    except ValueError as exc:
        st.error(str(exc))
        return
    st.caption(f'{len(actuales)} artículos en el Carrito actual. El historial se conserva dentro del archivo al guardar desde esta pantalla.')
    accion = st.radio('Qué querés hacer', ['Actualizar Carrito vigente', 'Recuperar datos de un Carrito anterior'],
                      key='accion_carrito_290')
    historico = accion == 'Recuperar datos de un Carrito anterior'
    referencia = Path(__file__).resolve().parents[1] / 'respaldo/Carrito_Referencia_Recuperado.xlsx'
    usar_referencia = historico and referencia.exists() and st.checkbox(
        'Usar el Carrito de referencia recuperado del ZIP original (incluye Delicia)', key='usar_respaldo_290')
    if usar_referencia:
        entrante = referencia.read_bytes()
        nombre = 'Carrito de referencia del ZIP original; fecha comercial no informada'
    else:
        archivo = st.file_uploader('Seleccionar Carrito anterior' if historico else 'Seleccionar Carrito nuevo',
                                   type=['xlsx'], key='cargar_carrito_hist_290' if historico else 'cargar_carrito_nuevo_290')
        if not archivo:
            if bloqueos:
                st.warning(f'{len(bloqueos)} códigos tienen cambios de presentación para revisar. Podés volver a cargar el Carrito actual para revisarlos.')
            return
        entrante, nombre = archivo.getvalue(), archivo.name
    fecha = st.date_input('Fecha del Carrito (si la conocés)', value=None,
                          max_value=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date(),
                          key='fecha_carrito_hist_290' if historico else 'fecha_carrito_nuevo_290')
    st.caption('La fecha corresponde al archivo del proveedor. Si no la conocés, quedará “Sin fecha informada”; también se registra cuándo se incorporó.')
    ok, errores, _ = validar_carrito(BytesIO(entrante))
    if not ok:
        for error in errores:
            st.error(error)
        return
    try:
        nuevos, _, _ = leer(entrante)
        cambios = comparar(original, entrante)
        huella = hashlib.sha256(original + entrante + str(fecha).encode() + accion.encode()).hexdigest()[:16]
        confirmados = []
        if historico:
            st.info('Esta operación conserva el Carrito vigente. El archivo anterior aporta respaldo para datos faltantes, sin reemplazar valores válidos ya conocidos.')
            candidato = preparar(original, entrante, nombre, fecha, historico=True)
            antes, despues = resolver(original), resolver(candidato)
            recuperados = []
            for cod, r in despues.items():
                campos = [c for c in ['precio', 'peso', 'cubicaje'] if antes.get(cod, {}).get(c) != r.get(c) and r.get(c) is not None]
                if campos:
                    recuperados.append({'Código': cod, 'Producto': r['descripcion'], 'Datos recuperados': ', '.join(campos),
                                        'Precio bulto': r['precio'], 'Cubicaje': r['cubicaje']})
            st.write(f'**{len(recuperados)} artículos recuperan datos conocidos.**')
            if recuperados:
                st.dataframe(pd.DataFrame(recuperados), hide_index=True, use_container_width=True)
        else:
            df = pd.DataFrame(cambios)
            if df.empty:
                st.info('Sin cambios en los artículos. Se conserva el historial.')
            else:
                contadores = df['cambio'].value_counts().to_dict()
                st.write(' · '.join(f'{k}: {v}' for k, v in contadores.items()))
                st.dataframe(df.rename(columns={'codigo':'Código','producto':'Producto','cambio':'Cambio','detalle':'Detalle'}),
                             hide_index=True, use_container_width=True)
            ausentes = len(set(actuales)-set(nuevos))
            fechas_guardadas = [r['fecha'] for r in historial if r.get('fecha') and not r.get('importado')]
            if fecha and fechas_guardadas and str(fecha) < max(fechas_guardadas):
                st.warning('La fecha indicada es anterior a la de un Carrito guardado. Revisá si corresponde recuperar un respaldo en vez de reemplazar el vigente.')
            if ausentes > len(actuales)*.2:
                st.warning(f'Desaparece más del 20% del catálogo ({ausentes} artículos). Verificá que no sea un archivo incompleto o anterior.')
            estructurales = sorted({r['codigo'] for r in cambios if r['cambio']=='Presentación para revisar'} | (set(bloqueos)&set(nuevos)))
            if estructurales:
                st.warning('Los cambios de descripción, peso o cubicaje conservan la referencia anterior y bloquean la compra de esos códigos hasta revisar la presentación.')
                confirmados = st.multiselect('Confirmo que estos códigos siguen representando la misma presentación física', estructurales,
                                             format_func=lambda c: f"{c} · {nuevos[c]['descripcion']}", key='mismos_packs_'+huella)
                st.caption('Marcá solo correcciones de nombre/datos de la misma presentación, también válida para tus existencias. Si cambió realmente el contenido del pack, dejalo pendiente para reconciliar el Maestro y el stock.')
            candidato = preparar(original, entrante, nombre, fecha, confirmar_misma_presentacion=confirmados)
        with st.expander('Referencias que quedarán guardadas'):
            refs = detalle_referencias(candidato)
            st.dataframe(pd.DataFrame(refs), hide_index=True, use_container_width=True)
        revision = huella + hashlib.sha256(','.join(sorted(confirmados)).encode()).hexdigest()[:8]
        revisado = st.checkbox('Revisé el archivo, la fecha y los cambios mostrados', key='revisado_carrito_'+revision)
        if st.button('Guardar respaldo histórico' if historico else 'Guardar Carrito e historial', type='primary', disabled=not revisado):
            guardar(github, original, candidato)
            for clave in ['pedido_descargas_labs','ultimo_analisis_snapshot','costos_mix_actual','informe_stock_bytes_260','data_status']:
                st.session_state.pop(clave, None)
            st.session_state['mensaje_carrito_290'] = 'Respaldo histórico guardado. Regenerá los informes.' if historico else 'Carrito actualizado e historial conservado. Regenerá los informes.'
            st.rerun()
    except Exception as exc:
        st.error(f'No se guardó ningún cambio: {exc}')


def mostrar_referencias_stock(carrito_path, codigos):
    refs = detalle_referencias(carrito_path, codigos)
    avisos = [r for r in refs if r['Estado'] != 'Vigente']
    if avisos:
        st.warning(f'{len(avisos)} productos del stock requieren datos históricos o revisión del Carrito. Conservan su asociación; no es necesario volver a vincular los que ya tienen código correcto.')
        with st.expander('Datos anteriores y advertencias del catálogo', expanded=True):
            st.dataframe(pd.DataFrame(avisos), hide_index=True, use_container_width=True)
    with st.expander('Consultar precio y cubicaje de los productos del stock'):
        st.dataframe(pd.DataFrame(refs), hide_index=True, use_container_width=True)
    return avisos
