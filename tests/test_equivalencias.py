from io import BytesIO
from pathlib import Path
import tempfile
import unittest
import pandas as pd
from openpyxl import load_workbook
import motor
from core.capacidad_camara import leer_bultos_stock, preparar_movimientos_camara
from core.alta_productos import preparar_producto
ROOT=Path(__file__).resolve().parents[1]

class EquivalenciasTests(unittest.TestCase):
    def setUp(self):
        self.m=ROOT/'data/Maestro_Productos_Grido.xlsx'
        self.p=motor.load_productos(self.m).set_index('Producto Base').to_dict('index')
        self.a={r['Alias Normalizado']:r.to_dict() for _,r in motor.load_aliases(self.m).iterrows()}
    def bultos(self,nombre,cantidad):
        a=motor.alias_lookup(nombre,self.a);b=a['Producto Base']
        eq,_=motor.convert_quantity(nombre,b,cantidad,a['Tipo Presentación'],a['Pack Detectado'],self.p)
        return eq/self.p[b]['Compra Mínima']
    def test_crocante_cajas_y_unidades(self):
        self.assertAlmostEqual(self.bultos('Bombon Crocante x Unidad',-36),-.75)
        self.assertAlmostEqual(self.bultos('Bombon Crocante en Caja x 8 Un.',6),1)
    def test_alfajor_y_limon(self):
        self.assertEqual(self.bultos('Alfajor Secreto Cookies and Cream x 6',54),9)
        self.assertEqual(self.bultos('Palito Frutal Limon en Caja x 20 Un.',65),13)
        self.assertAlmostEqual(self.bultos('Palito Frutal Limon x Unidad',-111),-1.11)
    def test_cajas_sin_tacc_y_unidad(self):
        self.assertEqual(self.bultos('Hsaa Chocolate S/Tacc X 12 Unid.',14),14)
        self.assertAlmostEqual(self.bultos('Hsaa Chocolate S/Tacc x Un.',12),1)
    def test_no_interpreta_gramos_como_unidades(self):
        self.assertEqual(self.bultos('Empanada de Carne Frizzio 4 u x 80g',18),1)
    def test_sin_dato_no_usa_compra_minima_como_divisor(self):
        p={'x':{'Compra Mínima':6,'Tipo Producto':'Fraccionable'}}
        n,_=motor.convert_quantity('x','x',36,'Unidad',None,p)
        self.assertTrue(pd.isna(n))
    def test_exclusion_global_y_camara_comparten_regla(self):
        filas=[['Bombones','Heladería','Impulsivos','Bombon Crocante x Unidad','-36','48','-100'],
               ['Tentación','Heladería','Impulsivos','Tentación 1 Lt Mascarpone','-3','12','-100'],
               ['Frizzio','Congelados','Frizzio','Papas McCain Smiles x 700grs.','14','14','-100']]
        with tempfile.TemporaryDirectory() as t:
            s=Path(t)/'stock.csv'
            pd.DataFrame(filas,columns=['Grupo','Rubro','SubRubro','Item','Stock','Tránsito','Bultos']).to_csv(s,sep=';',index=False)
            f=leer_bultos_stock(s,self.m)
            self.assertAlmostEqual(f['netos'],.25) # -.75 + 1 papa; ignora excluido general
            self.assertEqual(len(f['filas']),2)
            mov=preparar_movimientos_camara(s,self.m).set_index('Producto')
            self.assertNotIn('tentacion 1 lt mascarpone',mov.index)
            self.assertIn('papas mccain smiles x 700grs',mov.index) # omisión de compra no es exclusión física
            self.assertEqual(mov.loc['bombon crocante','Tránsito (eq)'],6)
    def test_editor_actualiza_equivalencia_y_reutiliza_dato(self):
        b,v=preparar_producto(self.m.read_bytes(),ROOT/'data/Modelo_de_Carrito.xlsx','bombon crocante','4000145',6,'Fraccionable',1,['Bombon Crocante x Unidad'],{'Bombon Crocante x Unidad':('Unidad',None)},unidades_base=8)
        p=motor.load_productos(BytesIO(b)).set_index('Producto Base').to_dict('index')
        eq,_=motor.convert_quantity('Bombon Crocante x Unidad','bombon crocante',-36,'Unidad',None,p)
        self.assertEqual(eq/6,-.75)
        w=load_workbook(BytesIO(b));self.assertEqual(list(w['Exclusiones'].values),list(load_workbook(self.m)['Exclusiones'].values))
