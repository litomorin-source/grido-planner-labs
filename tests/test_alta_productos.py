"""Pruebas del editor, sin guardar cambios en GitHub ni en datos del repositorio."""
from io import BytesIO
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import motor
from core.alta_productos import (preparar_producto, pendientes_stock, guardar_producto,
                                catalogo_carrito, ordenar_candidatos, MAESTRO, CARRITO)
from core.github_sync import GitHubSync


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.maestro = ROOT / 'data/Maestro_Productos_Grido.xlsx'
        self.carrito = ROOT / 'data/Modelo_de_Carrito.xlsx'
        self.original = self.maestro.read_bytes()

    def limon(self, **kw):
        args = dict(maestro_bytes=self.original, carrito_path=self.carrito,
                    base='palito frutal limon', codigo='4000857', minima=10,
                    tipo='Palito especial', peso=5.5,
                    nombres=['Palito Frutal Limon X10 U.', 'Palito Frutal Limon en Caja x 20 Un.',
                             'Palito Frutal Limon x Unidad'])
        args.update(kw)
        return preparar_producto(**args)

    def test_actualiza_codigo_y_equivalencia_sin_alterar_otras_hojas(self):
        data, vista = self.limon()
        self.assertFalse(vista['nuevo'])
        viejo = load_workbook(BytesIO(self.original))
        nuevo = load_workbook(BytesIO(data))
        for hoja in viejo.sheetnames:
            if hoja != 'Productos':
                self.assertEqual(list(viejo[hoja].values), list(nuevo[hoja].values))
        for antes, despues in zip(list(viejo['Productos'].values)[1:], list(nuevo['Productos'].values)[1:]):
            if antes[0] != 'palito frutal limon':
                self.assertEqual(antes, despues[:len(antes)])
        p = motor.load_productos(BytesIO(data)).set_index('Producto Base').loc['palito frutal limon']
        self.assertEqual(motor.normalizar_codigo_compra(p['Código Compra']), '4000857')
        fila_limon = next(r for r in nuevo['Productos'].iter_rows(min_row=2) if r[0].value == 'palito frutal limon')
        self.assertEqual(fila_limon[1].value, '4000857')
        self.assertEqual(fila_limon[1].number_format, '@')
        self.assertEqual(p['Compra Mínima'], 10)
        self.assertEqual(self.maestro.read_bytes(), self.original)
        self.assertEqual([v['Conversión a presentación base'] for v in vista['conversiones']],
                         ['cantidad', 'cantidad * 2', 'cantidad / 10'])

    def test_nuevo_producto_y_alias_con_carrito_actualizado(self):
        wb = load_workbook(self.carrito)
        ws = wb.active
        fila = ['H14- SABORES COMUNES','4999999',0,'1000','CREMA AL CIELO 7,800 KG GRIDO',.8,7.8,0,30000,10]
        ws.append(fila)
        with tempfile.TemporaryDirectory() as t:
            carrito = Path(t)/'carrito.xlsx'
            wb.save(carrito)
            data, vista = preparar_producto(self.original, carrito, 'crema al cielo', '4999999',
                                           1, 'Sabor 7,800 kg', 7.8, ['Crema Al Cielo 7,800 Kg  - Grido'],
                                           {'Crema Al Cielo 7,800 Kg  - Grido': ('Presentación base', None)}, 'Común')
        self.assertTrue(vista['nuevo'])
        p = motor.load_productos(BytesIO(data))
        self.assertEqual(len(p), len(motor.load_productos(self.maestro))+1)
        aliases = motor.load_aliases(BytesIO(data))
        self.assertIn('crema al cielo', set(aliases['Producto Base']))
        w = load_workbook(BytesIO(data))
        self.assertEqual(list(w['Productos'].values)[-1][-1], 7.8)

    def test_impide_datos_invalidos_y_codigo_duplicado(self):
        for args in [dict(minima=0), dict(minima=1.5), dict(peso=0), dict(codigo='0000000'),
                     dict(codigo='4000050'), dict(tipo='Otro')]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.limon(**args)

    def test_nuevo_alias_no_puede_cambiar_otro_producto(self):
        with self.assertRaisesRegex(ValueError, 'otro producto'):
            self.limon(nombres=['Alfajor Secreto Cookies and Cream x 6'])

    def test_guardado_rechaza_fuentes_modificadas_y_pasa_sha(self):
        github = Mock()
        github.download_file_bytes.side_effect = [dict(ok=True, content_bytes=b'cambio', sha='1'),
                                                  dict(ok=True, content_bytes=b'carrito')]
        with self.assertRaisesRegex(ValueError, 'cambió'):
            guardar_producto(github,b'maestro',b'carrito',b'nuevo')
        github.upload_bytes_file.assert_not_called()
        github.download_file_bytes.side_effect = [dict(ok=True, content_bytes=b'maestro',sha='version'),
                                                  dict(ok=True, content_bytes=b'carrito')]
        github.upload_bytes_file.return_value = dict(ok=True)
        guardar_producto(github,b'maestro',b'carrito',b'nuevo')
        self.assertEqual(github.upload_bytes_file.call_args.kwargs['expected_sha'], 'version')
        self.assertEqual(github.upload_bytes_file.call_args.kwargs['path'], MAESTRO)

    def test_sha_cambiado_no_envia_put(self):
        github = GitHubSync('prueba','prueba','main')
        with patch.object(github,'_get_existing_sha',return_value=dict(ok=True,sha='otro')):
            respuesta = github.upload_bytes_file(MAESTRO,b'x','prueba',expected_sha='anterior')
        self.assertFalse(respuesta['ok'])

    @unittest.skipUnless(os.environ.get('GRIDO_DATOS_PRUEBA'), 'Requiere informes privados')
    def test_pendientes_reales_y_recalculo_con_correccion(self):
        stock = Path(os.environ['GRIDO_DATOS_PRUEBA'])/'Stock_20261116_124624.csv'
        pendientes = pendientes_stock(stock,self.maestro,self.carrito)
        self.assertEqual({p['producto'] for p in pendientes}, {'crema al cielo','palito frutal limon'})
        crema = next(p for p in pendientes if p['producto']=='crema al cielo')
        self.assertEqual(crema['codigo'], '')
        candidatos = ordenar_candidatos('palito frutal limon',catalogo_carrito(self.carrito))
        self.assertEqual(candidatos[0]['codigo'],'4000857')
        data, _ = self.limon()
        with tempfile.TemporaryDirectory() as t:
            nuevo = Path(t)/'maestro.xlsx'
            nuevo.write_bytes(data)
            p = pendientes_stock(stock,nuevo,self.carrito)
            self.assertEqual({x['producto'] for x in p}, {'crema al cielo'})
            r = motor.procesar_costo_stock(stock,nuevo,Path(t)/'stock.xlsx',self.carrito)
            limon = r['detalle'].set_index('Producto').loc['palito frutal limon']
            self.assertEqual(limon['Precio Pack'],13643)
            self.assertGreater(limon['Valor Stock Actual'],0)


if __name__ == '__main__':
    unittest.main()
