"""Presentación compacta de GridoPlanner, separada del cálculo de pedidos."""
from html import escape
import pandas as pd
import streamlit as st
from core.presentacion import formato_bultos

SECCIONES = {"Pedido": "pedido", "Stock y cámara": "stock", "Costos": "costos",
             "Configuración": "config", "Pallets": "pallets"}


def aplicar_diseno(pagina, version):
    ocultas = ",".join(f".st-key-vista-{clave}" for nombre, clave in SECCIONES.items() if nombre != pagina)
    st.markdown(f"""<style>
    .block-container {{padding-top:4rem; padding-bottom:2rem; max-width:1400px;}}
    [data-testid="stSidebar"] {{min-width:225px; max-width:255px;}}
    [data-testid="stSidebar"] > div {{padding-top:1.5rem;}}
    h1 {{font-size:1.8rem!important;}} h2 {{font-size:1.4rem!important;}}
    h3 {{font-size:1.12rem!important;}}
    .gp-header {{display:flex;align-items:center;justify-content:space-between;margin:0 0 1.2rem;}}
    .gp-brand {{font-size:1.6rem;font-weight:750;color:#123552;letter-spacing:-.04em;}}
    .gp-version {{font-size:.73rem;color:#49677b;background:#eaf2f9;padding:.3rem .65rem;border-radius:30px;}}
    .gp-status {{font-size:.82rem;color:#4a6276;padding:.2rem 0;}}
    .gp-status strong {{color:#124b74;}}
    .gp-card {{border:1px solid #dfe8ef;background:white;border-radius:12px;padding:1rem;min-height:112px;box-shadow:0 3px 12px #153b5c06;}}
    .gp-card-label {{font-size:.78rem;color:#536b7c;margin-bottom:.4rem;}}
    .gp-card-value {{font-size:clamp(1.25rem,2vw,1.85rem);font-weight:750;color:#163f60;line-height:1.2;}}
    .gp-card-note {{font-size:.72rem;color:#647788;margin-top:.45rem;}}
    .gp-card-warning {{border-top:3px solid #c77a16;}}
    {ocultas} {{display:none!important;}}
    @media(max-width:700px){{.block-container{{padding:4rem 1rem 2rem;}} .gp-brand{{font-size:1.35rem;}}}}
    </style><div class="gp-header"><span class="gp-brand">GridoPlanner</span><span class="gp-version">{escape(version)}</span></div>""", unsafe_allow_html=True)


def render_resumen(result, proyeccion=None):
    pedido = result['pedido']
    problemas = set()
    for key in ('stock_negativo','posibles_faltantes','sin_clasificar','sin_precio'):
        df = result.get(key)
        if df is None or df.empty:
            continue
        col = 'Producto' if 'Producto' in df else 'Producto Base'
        problemas.update(df[col].dropna().astype(str))
    valor = f"$ {int(result.get('valor_pedido_total',0)):,}".replace(',', '.')
    parcial = result.get('pedido_valorizacion_incompleta',False)
    ocupacion = '—' if proyeccion is None else f"{proyeccion['ocupacion_pct']:.1f}%".replace('.',',')
    incompleta = proyeccion is not None and proyeccion.get('transito_sin_conversion',0)>0
    cards = [
        ('Importe sugerido',valor,'Subtotal conocido' if parcial else 'Productos del pedido',parcial),
        ('Packs a comprar',formato_bultos(pedido['Packs a Comprar'].sum()),f"{int(pedido['Packs a Comprar'].gt(0).sum())} productos con compra",False),
        ('Ocupación estimada',ocupacion,'Estimación incompleta' if incompleta else 'Según llegada estimada',incompleta or (proyeccion is not None and proyeccion['ocupacion_pct']>=90)),
        ('Productos para revisar',str(len(problemas)),'Ver alertas y datos pendientes',bool(problemas)),
    ]
    for columna,(label,value,note,warning) in zip(st.columns(4),cards):
        with columna:
            st.markdown(f'<div class="gp-card {"gp-card-warning" if warning else ""}"><div class="gp-card-label">{escape(label)}</div><div class="gp-card-value">{escape(value)}</div><div class="gp-card-note">{escape(note)}</div></div>',unsafe_allow_html=True)


def grafico_historial(df):
    """Un gráfico seleccionable; datos originales conservados para exportación."""
    col1,col2 = st.columns(2)
    tipo = col1.selectbox('Mostrar', ['Valor del stock','Bultos','Unidades equivalentes'],key='historial_metrica')
    periodo = col2.selectbox('Período', ['Últimos 30 días','Últimos 90 días','Todo'],index=1,key='historial_periodo')
    campo = {'Valor del stock':'valor_stock','Bultos':'bultos_netos','Unidades equivalentes':'cantidad_unidades'}[tipo]
    datos = df.dropna(subset=['fecha_orden',campo]).sort_values('fecha_orden').copy()
    if not datos.empty and periodo!='Todo':
        dias = 30 if periodo=='Últimos 30 días' else 90
        datos = datos[datos.fecha_orden >= df.fecha_orden.max()-pd.Timedelta(days=dias)]
    if datos.empty:
        st.info('No hay registros para este período.')
        return
    datos['Fecha'] = datos.fecha_orden.dt.strftime('%Y-%m-%dT%H:%M:%S')
    datos['Fecha visible'] = datos.fecha_orden.dt.strftime('%d/%m/%Y %H:%M')
    datos['Valor'] = datos[campo].round(0) if tipo=='Bultos' else datos[campo]
    datos['Estado'] = datos['valorizacion_completa'].fillna('').replace({'':'Sin verificar','No':'Subtotal incompleto','Sí':'Completo'})
    datos['Importe visible'] = datos['Valor'].map(lambda v: ('$ ' if tipo=='Valor del stock' else '')+f'{v:,.0f}'.replace(',','.'))
    axis = {'title':None,'labelColor':'#617487','gridColor':'#e9eff4'}
    if tipo=='Valor del stock':
        axis['labelExpr'] = "'$' + format(datum.value / 1000000, '.0f') + ' M'"
    else:
        axis['format'] = ',.0f'
    spec = {
        'height':260,'mark':{'type':'line','color':'#087bb8','strokeWidth':2.5,'point':{'size':35}},
        'encoding':{
            'x':{'field':'Fecha','type':'temporal','axis':{'title':None,'format':'%d/%m','grid':False}},
            'y':{'field':'Valor','type':'quantitative','axis':axis,'scale':{'zero':True}},
            'tooltip':[{'field':'Fecha visible','type':'nominal','title':'Fecha'},
                       {'field':'Importe visible','type':'nominal','title':tipo},
                       {'field':'Estado','type':'nominal','title':'Valorización'}],
        },'config':{'view':{'stroke':None}},
    }
    st.vega_lite_chart(datos[['Fecha','Fecha visible','Valor','Estado','Importe visible']],spec,use_container_width=True)
    st.caption('Las valorizaciones incompletas son subtotales. Período contado desde el último stock registrado.')
