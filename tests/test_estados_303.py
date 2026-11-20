from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock
import os
import pandas as pd
from openpyxl import load_workbook
import motor
from core.estados_productos import guardar_estados, leer_estados, MIGRACION
from core.presentacion import costos_a_excel
from core.costos_mix import calcular_costos_mix
from core.capacidad_camara import leer_bultos_stock

ROOT = Path(__file__).resolve().parents[1]

class EstadosTests(TestCase):
    def setUp(self):
        self.original = (ROOT/'data/Maestro_Productos_Grido.xlsx').read_bytes()
        self.gh = Mock()
        self.gh.download_file_bytes.return_value = dict(ok=True, sha='sha1', content_bytes=self.original)
        self.gh.upload_bytes_file.return_value = dict(ok=True)

    def guardar(self, cambios, pendientes=None):
        guardar_estados(self.gh, self.original, cambios, pendientes or [])
        args = self.gh.upload_bytes_file.call_args.kwargs
        self.assertEqual(args['expected_sha'], 'sha1')
        return args['content_bytes']

    def test_estados_reactivacion_y_preservacion(self):
        nuevo = self.guardar({'bombon crocante':'Discontinuado', 'vela prueba':'Excluido'})
        p = motor.load_productos(BytesIO(nuevo)).set_index('Producto Base')
        self.assertTrue(p.loc['bombon crocante','Activo'])
        self.assertFalse(p.loc['bombon crocante','Excluir'])
        self.assertEqual(p.loc['bombon crocante','Estado'],'Discontinuado')
        self.assertIn('vela prueba', motor.load_exclusiones(BytesIO(nuevo)))
        a = load_workbook(BytesIO(self.original)); b = load_workbook(BytesIO(nuevo))
        self.assertEqual(list(a['Aliases'].values),list(b['Aliases'].values))
        cols = ['Código Compra','Compra Mínima','Unidades por presentación base','Producto Compra']
        pd.testing.assert_frame_equal(motor.load_productos(BytesIO(self.original))[cols], p.reset_index()[cols])
        self.original = nuevo
        self.gh.download_file_bytes.return_value = dict(ok=True, sha='sha1', content_bytes=nuevo)
        final = self.guardar({'bombon crocante':'Activo', 'vela prueba':'Activo'})
        self.assertEqual(leer_estados(BytesIO(final))[0]['bombon crocante'],'Activo')
        self.assertNotIn('vela prueba', motor.load_exclusiones(BytesIO(final)))

    def test_migracion_parcial_y_conflicto(self):
        pendientes = [{'producto_base':n} for n in ['bombon crocante','vela prueba']]
        nuevo = self.guardar({'bombon crocante':'Discontinuado'}, pendientes)
        self.assertNotEqual(motor.load_config(BytesIO(nuevo)).get(MIGRACION), 'Sí')
        self.gh.upload_bytes_file.reset_mock()
        self.gh.download_file_bytes.return_value['content_bytes'] = nuevo
        with self.assertRaisesRegex(ValueError, 'cambió'):
            guardar_estados(self.gh,self.original,{'vela prueba':'Excluido'}, pendientes)
        self.gh.upload_bytes_file.assert_not_called()
        self.original = nuevo
        final = self.guardar({'vela prueba':'Excluido'}, [pendientes[1]])
        self.assertEqual(motor.load_config(BytesIO(final))[MIGRACION], 'Sí')

    def test_excel_costos(self):
        d = pd.DataFrame({'Producto':['a'], 'Costo reposición':[123.45], 'Kilos vendidos':[2.5], 'clave':['interno']})
        w = load_workbook(BytesIO(costos_a_excel(d)))
        s = w['Detalle']
        self.assertEqual(s['B2'].value, 123.45)
        self.assertIn('$', s['B2'].number_format)
        self.assertNotIn('$', s['C2'].number_format)
        self.assertEqual(s.max_column,3)
        self.assertEqual(s.freeze_panes,'A2')

    def test_pedido_costos_camara_y_reactivacion_reales(self):
        if not os.environ.get('GRIDO_DATOS_PRUEBA'):
            self.skipTest('Fixtures privados no disponibles')
        datos = Path(os.environ['GRIDO_DATOS_PRUEBA'])
        with TemporaryDirectory() as td:
            folder=Path(td); master=folder/'master.xlsx';master.write_bytes(self.original)
            stock=datos/'Stock_20261116_124624.csv'; sabores=datos/'Cajas por Sabor (43).xlsx'; mix=datos/'Kilos y Cantidades por Período (10).xlsx';cart=ROOT/'data/Modelo_de_Carrito.xlsx'
            args=dict(stock_file=stock,sabores_file=sabores,data_file=mix,maestro_file=master,carrito_file=cart,output_file=folder/'pedido.xlsx',overrides={'Semanas objetivo':4,'Tiempo de reposición':1,'Días analizados':14})
            base=motor.procesar_archivos(**args)['pedido'].set_index('Producto')
            camara=leer_bultos_stock(stock,master)['netos']
            costobase=calcular_costos_mix(sabores,mix,master,cart)[1]
            nuevo=self.guardar({'bombon crocante':'Discontinuado'});master.write_bytes(nuevo)
            pedido=motor.procesar_archivos(**args)['pedido'].set_index('Producto')
            self.assertEqual(pedido.loc['bombon crocante','Packs a Comprar'],0)
            self.assertGreater(base.loc['bombon crocante','Packs a Comprar'],0)
            self.assertEqual(pedido.loc['bombon crocante','Stock'],base.loc['bombon crocante','Stock'])
            pd.testing.assert_frame_equal(base.drop('bombon crocante'),pedido.drop('bombon crocante'))
            self.assertEqual(leer_bultos_stock(stock,master)['netos'],camara)
            pd.testing.assert_frame_equal(costobase,calcular_costos_mix(sabores,mix,master,cart)[1])
            # Otra cobertura de compra: sigue sin pedirlo.
            self.assertEqual(motor.procesar_archivos(**dict(args,overrides={'Semanas objetivo':8,'Tiempo de reposición':1,'Días analizados':14}))['pedido'].set_index('Producto').loc['bombon crocante','Packs a Comprar'],0)
            self.original=nuevo;self.gh.download_file_bytes.return_value['content_bytes']=nuevo
            excluido=self.guardar({'bombon crocante':'Excluido'});master.write_bytes(excluido)
            self.assertNotIn('bombon crocante',motor.procesar_archivos(**args)['pedido']['Producto'].tolist())
            self.assertNotEqual(leer_bultos_stock(stock,master)['netos'],camara)
            costos=calcular_costos_mix(sabores,mix,master,cart)[1]
            self.assertLess(len(costos),len(costobase))
            self.original=excluido;self.gh.download_file_bytes.return_value['content_bytes']=excluido
            master.write_bytes(self.guardar({'bombon crocante':'Activo'}))
            pd.testing.assert_frame_equal(base,motor.procesar_archivos(**args)['pedido'].set_index('Producto'))

    def test_historico_stock_cero_y_transito_que_compensa(self):
        if not os.environ.get('GRIDO_DATOS_PRUEBA'):
            self.skipTest('Fixtures privados no disponibles')
        from unittest.mock import patch
        datos = Path(os.environ['GRIDO_DATOS_PRUEBA'])
        with TemporaryDirectory() as td:
            folder=Path(td);stock=folder/'stock.csv'
            raw=pd.read_csv(datos/'Stock_20261116_124624.csv',sep=';',dtype=str)
            raw['Stock']='0';raw['Tránsito']='0';raw.to_csv(stock,sep=';',index=False)
            # Todas las referencias como históricas: ninguna debe advertir sin existencias.
            from core.catalogo import resolver
            refs=resolver(ROOT/'data/Modelo_de_Carrito.xlsx')
            for ref in refs.values():ref.setdefault('fuentes',{})['precio']='Histórico'
            args=dict(stock_file=stock,maestro_file=ROOT/'data/Maestro_Productos_Grido.xlsx',carrito_file=ROOT/'data/Modelo_de_Carrito.xlsx',output_file=folder/'stock.xlsx')
            with patch('core.catalogo.resolver',return_value=refs):
                self.assertFalse(motor.procesar_costo_stock(**args)['usa_costos_historicos'])
                idx=raw.index[raw['Item'].str.contains('Crocante',case=False)][0]
                raw.loc[idx,'Stock']='-1';raw.loc[idx,'Tránsito']='1';raw.to_csv(stock,sep=';',index=False)
                self.assertTrue(motor.procesar_costo_stock(**args)['usa_costos_historicos'])
