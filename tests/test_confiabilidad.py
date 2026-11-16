"""Regresión local; no conecta ni escribe en GitHub.

GRIDO_DATOS_PRUEBA=/carpeta/con/los/4/archivos python -m unittest discover -s tests -v
"""
import copy
import os
from pathlib import Path
import sys
import tempfile
import types
from io import BytesIO
import unittest
from unittest.mock import patch
import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import motor
from core.estado_analisis import huella_analisis, invalidar_si_cambio
from core.capacidad_camara import leer_bultos_stock, preparar_movimientos_camara, proyectar_capacidad


class EstadoTests(unittest.TestCase):
    def test_estado_anterior_sin_huella_invalida(self):
        estado = {'pedido_descargas_labs':'versión anterior'}
        self.assertTrue(invalidar_si_cambio(estado, 'nuevo'))
        self.assertNotIn('pedido_descargas_labs', estado)

    def test_identicos_conservan_descargas(self):
        h = huella_analisis({'stock': b'1'}, {'dias': 14}, [])
        estado = {'huella_insumos_labs': h, 'pedido_descargas_labs': 'ok'}
        self.assertFalse(invalidar_si_cambio(estado, huella_analisis({'stock': b'1'}, {'dias': 14.0}, [])))
        self.assertEqual(estado['pedido_descargas_labs'], 'ok')

    def test_cada_insumo_invalida(self):
        h = huella_analisis({'stock': b'1', 'maestro': b'm', 'carrito': b'c'}, {'dias': 14}, [])
        for archivos, params, om in [
            ({'stock': b'2', 'maestro': b'm', 'carrito': b'c'}, {'dias':14}, []),
            ({'stock': b'1', 'maestro': b'n', 'carrito': b'c'}, {'dias':14}, []),
            ({'stock': b'1', 'maestro': b'm', 'carrito': b'd'}, {'dias':14}, []),
            ({'stock': b'1', 'maestro': b'm', 'carrito': b'c'}, {'dias':7}, []),
            ({'stock': b'1', 'maestro': b'm', 'carrito': b'c'}, {'dias':14}, [{'producto_base':'vainilla'}]),
        ]:
            with self.subTest(params=params, archivos=archivos, om=om):
                estado = {'huella_insumos_labs': h, 'pedido_descargas_labs':'old', 'ultimo_analisis_snapshot':'old', 'costos_mix_actual':'old'}
                self.assertTrue(invalidar_si_cambio(estado, huella_analisis(archivos, params, om)))
                self.assertNotIn('pedido_descargas_labs', estado)
                self.assertNotIn('ultimo_analisis_snapshot', estado)
                self.assertNotIn('costos_mix_actual', estado)


class CamaraTests(unittest.TestCase):
    def test_transito_y_consumo_fisico(self):
        p = pd.DataFrame([{'Producto':'a', 'Grupo':'Helado', 'Ventas 14 días':100, 'Packs a Comprar':2, 'Compra Mínima':1}])
        mov = pd.DataFrame([{'Producto':'a','Stock físico (eq)':10,'Tránsito (eq)':40,'Compra Mínima':1,'Tránsito sin conversión':0}])
        r = proyectar_capacidad(p, 10, 14, 1, 100, movimientos_stock=mov)
        self.assertEqual(r['consumo_esperado_bultos'], 10)
        self.assertEqual(r['bultos_al_recibir'], 42)
        sin = proyectar_capacidad(p, 10, 14, 1, 100, movimientos_stock=mov, incluir_transito=False)
        self.assertEqual(sin['bultos_al_recibir'], 2)

    def test_omitidos_siguen_ocupando_camara_y_desconocidos_avisan(self):
        p = pd.DataFrame([{'Producto':'a','Grupo':'Helado','Ventas 14 días':0,'Packs a Comprar':0,'Compra Mínima':1}])
        mov = pd.DataFrame([
            {'Producto':'omitido','Stock físico (eq)':4,'Tránsito (eq)':6,'Compra Mínima':2,'Tránsito sin conversión':0},
            {'Producto':'desconocido','Stock físico (eq)':0,'Tránsito (eq)':7,'Compra Mínima':0,'Tránsito sin conversión':1}])
        r = proyectar_capacidad(p, 2, 14, 1, 10, movimientos_stock=mov)
        self.assertEqual(r['transito_bultos'], 3)
        self.assertEqual(r['transito_sin_conversion'], 1)
        self.assertEqual(r['bultos_al_recibir'], 5)


@unittest.skipUnless(os.environ.get('GRIDO_DATOS_PRUEBA'), 'Faltan archivos privados de prueba')
class ArchivosRealesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.datos = Path(os.environ['GRIDO_DATOS_PRUEBA'])
        cls.tmp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.tmp.name)
        cls.args = dict(stock_file=cls.datos/'Stock_20261116_124624.csv',
                        sabores_file=cls.datos/'Cajas por Sabor (43).xlsx',
                        data_file=cls.datos/'Kilos y Cantidades por Período (10).xlsx',
                        maestro_file=ROOT/'data/Maestro_Productos_Grido.xlsx',
                        carrito_file=ROOT/'data/Modelo_de_Carrito.xlsx',
                        output_file=cls.output/'pedido.xlsx',
                        overrides={'Semanas objetivo':4,'Tiempo de reposición':1,'Días analizados':14})
        cls.r = motor.procesar_archivos(**cls.args)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_reproduce_pedido_referencia(self):
        p = self.r['pedido']
        ref = pd.read_excel(self.datos/'Pedido_Final (42).xlsx', sheet_name='Pedido Final')
        self.assertEqual(int(p['Packs a Comprar'].sum()), 185)
        self.assertEqual(self.r['valor_pedido_total'], 5007851)
        compra = p[p['Packs a Comprar'].gt(0)].set_index('Producto')
        compra_ref = ref[ref['Packs a Comprar'].gt(0)].set_index('Producto')
        pd.testing.assert_series_equal(compra['Packs a Comprar'].sort_index(), compra_ref['Packs a Comprar'].sort_index(), check_dtype=False)
        comunes = p.merge(ref,on='Producto',suffixes=('_nuevo','_ref'))
        for c in ['Stock','Ventas 14 días','Packs a Comprar']:
            self.assertLess((comunes[c+'_nuevo']-comunes[c+'_ref']).abs().max(), .011)

    def test_precio_desconocido_no_es_cero(self):
        p = self.r['pedido'].set_index('Producto')
        self.assertTrue(pd.isna(p.loc['palito frutal limon','Precio Pack']))
        self.assertTrue(pd.isna(p.loc['palito frutal limon','Valor Stock Actual']))
        self.assertTrue(self.r['stock_valorizacion_incompleta'])
        self.assertFalse(self.r['pedido_valorizacion_incompleta'])
        w = load_workbook(self.output/'pedido.xlsx', data_only=True)
        self.assertIn('Sin precio',w.sheetnames)

    def test_precio_faltante_en_compra_marca_subtotal(self):
        precios = motor.load_precios_carrito(self.args['carrito_file'])
        fila = self.r['pedido'].query('`Packs a Comprar` > 0').iloc[0]
        precios.pop(motor.normalizar_codigo_compra(fila['Código Compra']))
        args = dict(self.args, output_file=self.output/'sin_precio.xlsx')
        with patch.object(motor, 'load_precios_carrito', return_value=precios):
            r = motor.procesar_archivos(**args)
        self.assertTrue(r['pedido_valorizacion_incompleta'])
        self.assertAlmostEqual(r['valor_pedido_total'],5007851-float(fila['Valor Pedido Sugerido']))
        p = r['pedido'].set_index('Producto')
        self.assertTrue(pd.isna(p.loc[fila['Producto'],'Valor Pedido Sugerido']))

    def test_camara_real(self):
        b = leer_bultos_stock(self.args['stock_file'])
        mov = preparar_movimientos_camara(self.args['stock_file'], self.args['maestro_file'])
        r = proyectar_capacidad(self.r['pedido'],b['netos'],14,1,movimientos_stock=mov)
        self.assertAlmostEqual(b['netos'],659.71)
        self.assertAlmostEqual(r['transito_bultos'],628.1833333333)
        self.assertEqual(r['transito_sin_conversion'],1)
        self.assertGreater(r['ocupacion_pct'],100)
        print('\nCÁMARA:',{k:v for k,v in r.items() if k!='detalle'})

    def test_informe_stock(self):
        r = motor.procesar_costo_stock(self.args['stock_file'],self.args['maestro_file'],self.output/'stock.xlsx',self.args['carrito_file'])
        self.assertTrue(r['stock_valorizacion_incompleta'])
        w = load_workbook(self.output/'stock.xlsx',data_only=True)
        self.assertIn('incompleto',w['Resumen']['A2'].value)
        self.assertIn('Sin precio',w.sheetnames)

    def test_identificacion_y_carrito_importable(self):
        # Adaptador mínimo solo para importar funciones puras de la UI.
        # No equivale a una prueba visual de Streamlit.
        with patch.dict(sys.modules, {'streamlit':types.SimpleNamespace(fragment=lambda f:f), 'requests':types.SimpleNamespace()}):
            from ui.home import identificar_archivo_operativo, generar_carrito_importacion, maestro_para_pedido
        for clave, tipo in [('stock_file','stock'),('sabores_file','sabores'),('data_file','data')]:
            path = self.args[clave]
            self.assertEqual(identificar_archivo_operativo(path.name,path.read_bytes())[0],tipo)
        data, productos, packs = generar_carrito_importacion(self.r['pedido'],self.args['carrito_file'])
        self.assertEqual(packs,185)
        w = load_workbook(BytesIO(data),data_only=True)
        headers = {c.value:c.column for c in w.active[1]}
        for row in list(w.active.values)[1:]:
            self.assertIsInstance(row[headers['Codigo']-1], str)
            self.assertIsInstance(row[headers['Cantidad']-1], int)
        omisiones = pd.read_csv(ROOT/'data/Omisiones_Futuros_Pedidos.csv').to_dict('records')
        maestro = maestro_para_pedido(self.args['maestro_file'],self.output,omisiones)
        r = motor.procesar_archivos(**dict(self.args,maestro_file=maestro,output_file=self.output/'omitidos.xlsx'))
        self.assertEqual(len(r['pedido']),95)
        self.assertEqual(r['valor_pedido_total'],5007851)
        self.assertEqual(int(r['pedido']['Packs a Comprar'].sum()),185)


if __name__ == '__main__':
    unittest.main()
