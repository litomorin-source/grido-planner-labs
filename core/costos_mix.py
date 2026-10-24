"""Análisis del costo actual de reposición de ventas (no CMV contable)."""
import pandas as pd
import numpy as np
from motor import (load_config,load_productos,load_aliases,load_exclusiones,load_precios_carrito,
                   read_sabores,read_data,normalize,normalizar_codigo_compra,safe_num)


def calcular_costos_mix(sabores_file, data_file, maestro_file, carrito_file):
    productos=load_productos(maestro_file)
    productos=productos[productos['Activo'] & ~productos['Excluir']].copy()
    pmap=productos.set_index('Producto Base').to_dict('index')
    am={}
    for _,r in load_aliases(maestro_file).iterrows():
        am[r['Alias Normalizado']]={'Producto Base':r['Producto Base'],
          'Tipo Presentación':r.get('Tipo Presentación',''), 'Pack Detectado':r.get('Pack Detectado',np.nan),
          'Regla Conversión':r.get('Regla Conversión',''), 'Alias Encontrado':True}
    exc=load_exclusiones(maestro_file)
    precios=load_precios_carrito(carrito_file)
    sabores=read_sabores(sabores_file,am,pmap,exc)
    mix=read_data(data_file,load_config(maestro_file),am,pmap,exc)

    # Kilos de Mix: tomados del archivo original, nunca supuestos desde la cantidad.
    raw=pd.read_excel(data_file)
    cc={normalize(c):c for c in raw.columns}
    nuevo='cant acum p1' in cc
    if nuevo:
        kilos_col=next((c for c in raw.columns if str(c).strip().lower().startswith('kilos acum. p1')), None)
        prod_col=cc.get('producto')
        if kilos_col is None or prod_col is None:
            raise ValueError('Mix P1 sin columnas de kilos o producto.')
        k=raw[[prod_col,kilos_col]].copy()
        k.columns=['Nombre original','Kilos vendidos']
    else:
        if raw.shape[1]!=16: raise ValueError('Mix no reconocido')
        raw.columns=['Categoria','SubCategoria','Grupo','Producto','PL_Cant','PL_Fact','PL_Kilos','PL_Porc','Promo_Cant','Promo_Fact','Promo_Kilos','Promo_Porc','Total_Cantidad','Total_Fact','Total_Kilos','Total_Porc']
        raw=raw.iloc[1:]
        k=raw[['Producto','Total_Kilos']].copy(); k.columns=['Nombre original','Kilos vendidos']
    k['Kilos vendidos']=pd.to_numeric(k['Kilos vendidos'].astype(str).str.replace('.','',regex=False).str.replace(',','.',regex=False),errors='coerce') if k['Kilos vendidos'].dtype=='object' else pd.to_numeric(k['Kilos vendidos'],errors='coerce')
    k['clave']=k['Nombre original'].astype(str).map(normalize)
    k=k.groupby('clave',as_index=False)['Kilos vendidos'].sum()

    registros=[]
    for grupo,df in [('Granel',sabores),('Envasados',mix)]:
        for _,r in df.iterrows():
            base=r['Producto Base']; cantidad=safe_num(r['Cantidad Eq']); pr=pmap.get(base,{})
            codigo=normalizar_codigo_compra(pr.get('Código Compra',''))
            minimo=safe_num(pr.get('Compra Mínima',1),1)
            precio=precios.get(codigo,0)
            costo=(cantidad/minimo*precio) if minimo>0 and precio>0 else None
            kilos=(cantidad*7.8) if grupo=='Granel' else None
            registros.append({'Grupo':grupo,'Producto':base,'Nombre original':r['Nombre original'],
                              'Unidades equivalentes':cantidad,'Kilos vendidos':kilos,
                              'Costo reposición':costo,'Código compra':codigo,
                              'Observación':('Sin costo/maestro' if costo is None else '')})
    detalle=pd.DataFrame(registros)
    if detalle.empty: raise ValueError('No se detectaron ventas para calcular costos.')
    es_mix=detalle['Grupo'].eq('Envasados')
    detalle.loc[es_mix,'clave']=detalle.loc[es_mix,'Nombre original'].astype(str).map(normalize)
    kilos_map = dict(zip(k['clave'], k['Kilos vendidos']))
    detalle.loc[es_mix,'Kilos vendidos']=detalle.loc[es_mix,'clave'].apply(lambda nombre: float(kilos_map.get(nombre, float('nan'))))
    detalle['Kilos vendidos']=pd.to_numeric(detalle['Kilos vendidos'],errors='coerce')
    detalle.loc[(detalle['Kilos vendidos']<=0) | detalle['Kilos vendidos'].isna(),'Observación'] = detalle['Observación'].fillna('') + ' Kilos no disponibles'
    resultados=[]
    for grupo,d in [('Granel',detalle[detalle.Grupo=='Granel']),('Envasados',detalle[detalle.Grupo=='Envasados']),('General',detalle)]:
        ok=d[d['Costo reposición'].notna() & d['Kilos vendidos'].notna() & d['Kilos vendidos'].gt(0)]
        costo=ok['Costo reposición'].sum(); kilos=ok['Kilos vendidos'].sum()
        resultados.append({'Grupo':grupo,'Costo de reposición':round(float(costo),2),
                           'Kilos valorizados':round(float(kilos),3),
                           'Costo por kg':round(float(costo/kilos),2) if kilos else None,
                           'Productos valorizados':len(ok),'Productos detectados':len(d),
                           'Cobertura productos (%)':round(100*len(ok)/len(d),1) if len(d) else 0})
    return pd.DataFrame(resultados),detalle
