import os
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from core.costos_mix import calcular_costos_mix

class CoberturaMovimientos(unittest.TestCase):
    def test_sin_movimiento_no_penaliza_y_faltantes_reales_permanecen(self):
        productos=pd.DataFrame([{'Producto Base':'alfajor','Activo':True,'Excluir':False,'Código Compra':'1','Compra Mínima':6}])
        filas=pd.DataFrame([{'Producto Base':'alfajor','Cantidad Eq':n,'Nombre original':nombre} for nombre,n in [('viejo',0),('actual',40),('sin peso',2)]])
        raw=pd.DataFrame({'Producto':['viejo','actual','sin peso'],'Cant. acum. P1':[None,40,2],'Kilos acum. P1':[None,20,None]})
        with patch('core.costos_mix.load_productos',return_value=productos), patch('core.costos_mix.load_aliases',return_value=pd.DataFrame()), patch('core.costos_mix.load_exclusiones',return_value=set()), patch('core.costos_mix.load_config',return_value={}), patch('core.costos_mix.load_precios_carrito',return_value={'1':60}), patch('core.catalogo.resolver',return_value={}), patch('core.catalogo.precios_compatibles',side_effect=lambda p,*a:p), patch('core.costos_mix.read_sabores',return_value=filas.iloc[:0]), patch('core.costos_mix.read_data',return_value=filas), patch('core.costos_mix.pd.read_excel',return_value=raw):
            resumen,detalle=calcular_costos_mix(None,None,None,None)
            self.assertEqual(detalle['Nombre original'].tolist(),['actual','sin peso'])
            general=resumen[resumen.Grupo=='General'].iloc[0]
            self.assertEqual(general['Cobertura productos (%)'],50)
            self.assertEqual(general['Productos sin kilos'],1)
            with patch('core.costos_mix.load_precios_carrito',return_value={}):
                resumen,detalle=calcular_costos_mix(None,None,None,None)
                self.assertTrue(detalle['Costo reposición'].isna().all())
                self.assertEqual(resumen[resumen.Grupo=='General'].iloc[0]['Cobertura productos (%)'],0)
