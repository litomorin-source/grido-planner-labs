from io import BytesIO
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import Mock
from openpyxl import Workbook, load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.catalogo import preparar, resolver, leer, comparar, guardar, ajustar_compra, precios_compatibles, HOJA


def carrito(filas):
    wb = Workbook()
    ws = wb.active
    ws.title = 'data'
    ws.append(['GrupoProducto','Codigo','Cantidad','Deposito','Descripcion','Cubicaje','Peso',
               'impuestoIva','precio','Disponible','maximo','minimo','multiplo'])
    for cod, precio, descripcion, peso, cubicaje in filas:
        ws.append(['Grupo',cod,0,'1000',descripcion,cubicaje,peso,0,precio,1000,9999999,0,1])
    b = BytesIO(); wb.save(b)
    return b.getvalue()


class CatalogoTests(unittest.TestCase):
    def setUp(self):
        self.antes = carrito([('1',100,'PACK X4',2,.5),('2',200,'DELICIA X4',2.4,.513)])
        self.nuevo = carrito([('1',120,'PACK X4',2,.5),('3',300,'NUEVO',1,1)])

    def test_desaparece_se_valoriza_y_reaparece_sin_perder_historial(self):
        actualizado = preparar(self.antes,self.nuevo,'nuevo','2026-11-16')
        r = resolver(actualizado)
        self.assertEqual(r['1']['precio'],120)
        self.assertEqual(r['1']['fecha_precio'],'2026-11-16')
        self.assertEqual(r['2']['precio'],200)
        self.assertEqual(r['2']['cubicaje'],.513)
        self.assertEqual(r['2']['fuentes']['precio'],'Histórico')
        self.assertFalse(r['2']['comprable'])
        self.assertEqual(ajustar_compra(3,r['2'])[0],3)
        reaparece = preparar(actualizado,self.antes,'vuelve','2026-11-17')
        self.assertTrue(resolver(reaparece)['2']['comprable'])
        self.assertEqual(resolver(reaparece)['2']['fuentes']['precio'],'Actual')
        self.assertTrue(any(c['cambio']=='Reaparece' and c['codigo']=='2' for c in comparar(actualizado,self.antes)))

    def test_precio_invalido_no_pisa_valor_previo_ni_habilita_compra(self):
        for precio in [None,0,-2]:
            with self.subTest(precio=precio):
                nuevo = carrito([('1',precio,'PACK X4',2,None)])
                r = resolver(preparar(self.antes,nuevo,'inválido'))['1']
                self.assertEqual(r['precio'],100)
                self.assertEqual(r['cubicaje'],.5)
                self.assertEqual(r['fuentes']['precio'],'Histórico')
                self.assertFalse(r['comprable'])

    def test_cambio_presentacion_no_mezcla_datos_y_requiere_revision(self):
        nuevo = carrito([('1',500,'PACK X10',5,1.5)])
        protegido = preparar(self.antes,nuevo,'nuevo')
        r = resolver(protegido)['1']
        self.assertEqual((r['precio'],r['peso'],r['cubicaje']),(100,2,.5))
        self.assertTrue(r['revisar'])
        self.assertFalse(r['comprable'])
        aprobado = preparar(protegido,nuevo,'revisado',confirmar_misma_presentacion=['1'])
        self.assertEqual(resolver(aprobado)['1']['precio'],500)
        self.assertFalse(resolver(aprobado)['1']['revisar'])

    def test_recuperacion_anterior_conserva_catalogo_actual_y_prioridad(self):
        recuperado = preparar(self.nuevo,self.antes,'archivo anterior','2026-10-01',historico=True)
        self.assertEqual(leer(recuperado)[0],leer(self.nuevo)[0])
        r = resolver(recuperado)
        self.assertEqual(r['1']['precio'],120)
        self.assertEqual(r['2']['precio'],200)
        self.assertEqual(r['2']['fecha_precio'],'2026-10-01')
        viejo = carrito([('1',1,'PACK X4',2,.5),('2',100,'DELICIA X4',2.4,.513)])
        otra = preparar(recuperado,viejo,'más viejo','2026-09-01',historico=True)
        self.assertEqual(resolver(otra)['2']['precio'],200)
        reciente = preparar(otra,viejo,'histórico más reciente','2026-11-01',historico=True)
        self.assertEqual(resolver(reciente)['2']['precio'],100)

    def test_datos_sin_fecha_no_inventan_fecha_comercial(self):
        r = resolver(preparar(self.nuevo,self.antes,'origen sin fecha',historico=True))['2']
        self.assertEqual(r['fecha_precio'],'')
        self.assertEqual(r['archivo_precio'],'origen sin fecha')

    def test_fecha_en_carga_identica_y_no_duplica_carga_repetida(self):
        p = preparar(self.antes,self.antes,'mismo','2026-11-16')
        self.assertEqual(resolver(p)['1']['fecha_precio'],'2026-11-16')
        q = preparar(p,self.antes,'mismo','2026-11-16')
        self.assertEqual(len(leer(p)[1]),len(leer(q)[1]))

    def test_duplicados_y_historial_corrupto_se_rechazan(self):
        with self.assertRaisesRegex(ValueError,'repetido'):
            leer(carrito([('1',1,'A',1,1),('1',2,'B',1,1)]))
        wb = load_workbook(BytesIO(preparar(self.antes,self.nuevo,'nuevo')))
        wb[HOJA].cell(2,1,'JSON inválido')
        b=BytesIO();wb.save(b)
        with self.assertRaisesRegex(ValueError,'historial'):
            leer(b.getvalue())

    def test_carrito_no_cambia_necesidad_de_compra(self):
        for referencia in [None, {}, dict(presente=False), dict(revisar=True),
                           dict(precio=0), dict(minimo=10), dict(maximo=0),
                           dict(disponible=0), dict(multiplo=3), dict(multiplo=.5),
                           dict(disponible=-1), dict(minimo=4,multiplo=3,maximo=8)]:
            for cantidad in [0, 2, 14, 20]:
                with self.subTest(referencia=referencia,cantidad=cantidad):
                    resultado, aviso = ajustar_compra(cantidad, referencia)
                    self.assertEqual(resultado, cantidad)
                    if cantidad:
                        self.assertTrue(aviso)

    def test_renombrar_no_bloquea_ni_descarta_costo_historico(self):
        import pandas as pd
        nuevo = carrito([('1',120,'OTRO NOMBRE',2,.5)])
        r = resolver(preparar(self.antes,nuevo,'renombrado'))['1']
        self.assertFalse(r['revisar'])
        self.assertEqual(r['precio'],120)
        r['fuentes']['precio']='Histórico'
        maestro=pd.DataFrame([{'Código Compra':'1','Producto Compra':'NOMBRE ANTERIOR','Peso Compra (kg)':2}])
        self.assertEqual(precios_compatibles({'1':120},{'1':r},maestro),{'1':120})

    def test_conflicto_no_guarda_y_exito_usa_sha(self):
        github=Mock()
        github.download_file_bytes.return_value=dict(ok=True,sha='nuevo',content_bytes=b'cambio')
        with self.assertRaisesRegex(ValueError,'cambió'):
            guardar(github,self.antes,self.nuevo)
        github.upload_bytes_file.assert_not_called()
        github.download_file_bytes.return_value=dict(ok=True,sha='version',content_bytes=self.antes)
        github.upload_bytes_file.return_value=dict(ok=True)
        guardar(github,self.antes,self.nuevo)
        self.assertEqual(github.upload_bytes_file.call_args.kwargs['expected_sha'],'version')

    def test_no_cruza_costo_historico_con_presentacion_distinta_del_maestro(self):
        import pandas as pd
        refs=resolver(preparar(self.nuevo,self.antes,'anterior',historico=True))
        precio={'2':200}
        m=pd.DataFrame([{'Código Compra':'2','Producto Compra':'DELICIA X8','Peso Compra (kg)':4.8}])
        self.assertEqual(precios_compatibles(precio,refs,m),{})
        m.loc[0,'Producto Compra']='DELICIA X4';m.loc[0,'Peso Compra (kg)']=2.4
        self.assertEqual(precios_compatibles(precio,refs,m),precio)

    @unittest.skipUnless(os.environ.get('GRIDO_CARRITO_ANTERIOR') and os.environ.get('GRIDO_CARRITO_NUEVO'), 'Requiere archivos actualizados privados')
    def test_delicia_real_y_asociacion_limon_conservada(self):
        import motor
        from core.alta_productos import pendientes_stock
        nuevo = Path(os.environ['GRIDO_CARRITO_NUEVO'])
        maestro = Path(os.environ['GRIDO_MAESTRO_NUEVO'])
        stock = Path(os.environ['GRIDO_DATOS_PRUEBA'])/'Stock_20261116_124624.csv'
        recuperado = preparar(nuevo,Path(os.environ['GRIDO_CARRITO_ANTERIOR']),'ZIP original',historico=True)
        d = resolver(recuperado)['4000593']
        self.assertEqual((d['precio'],d['cubicaje'],d['peso']),(13145.26,.513,2.4))
        self.assertFalse(d['comprable'])
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'carrito.xlsx';path.write_bytes(recuperado)
            r=motor.procesar_costo_stock(stock,maestro,Path(t)/'stock.xlsx',path)
            detalle=r['detalle'].set_index('Producto')
            self.assertEqual(detalle.loc['barra delicia chocolate y mani','Origen precio'],'Histórico')
            self.assertEqual(motor.normalizar_codigo_compra(detalle.loc['palito frutal limon','Código Compra']),'4000857')
            self.assertEqual(detalle.loc['palito frutal limon','Compra Mínima'],10)
            self.assertNotIn('barra delicia chocolate y mani',{p['producto'] for p in pendientes_stock(stock,maestro,path)})
            wb = load_workbook(Path(t)/'stock.xlsx')
            self.assertIn('Referencias catálogo', wb.sheetnames)
            wb.close()


if __name__=='__main__':
    unittest.main()
