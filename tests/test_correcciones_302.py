from io import BytesIO
from pathlib import Path
from unittest.mock import Mock
import unittest
from openpyxl import Workbook, load_workbook
from core.presentacion import formatear_monedas_excel
from core.capacidad_camara import guardar_capacidad, PARAMETRO_CAPACIDAD
from motor import load_config

class Correcciones302(unittest.TestCase):
    def test_moneda_en_hojas_y_encabezados_desplazados(self):
        w=Workbook();s=w.active
        s.append(['Advertencia']);s.append([])
        s.append(['Precio Pack','Costo Unitario Eq','Precio bulto','precio','Packs a Comprar','Cobertura (%)','Fecha precio'])
        s.append([123.45, 0, -14.2, 16.98, 3, 100, 'Sin fecha'])
        resumen=w.create_sheet('Resumen');resumen.append(['Concepto','Valor']);resumen.append(['Valor stock actual',1200]);resumen.append(['Productos valorizados',4])
        antes=[c.value for c in s[4]]
        formatear_monedas_excel(w)
        for c in list(s[4])[:4]:self.assertIn('$',c.number_format)
        for c in list(s[4])[4:]:self.assertNotIn('$',c.number_format)
        self.assertEqual([c.value for c in s[4]],antes)
        self.assertIn('$',resumen['B2'].number_format)
        self.assertNotIn('$',resumen['B3'].number_format)

    def test_capacidad_persistida_sin_cambiar_productos(self):
        original=(Path(__file__).resolve().parents[1]/'data/Maestro_Productos_Grido.xlsx').read_bytes()
        github=Mock();github.download_file_bytes.return_value={'ok':True,'sha':'v1','content_bytes':original}
        github.upload_bytes_file.return_value={'ok':True}
        guardar_capacidad(github,original,1240)
        args=github.upload_bytes_file.call_args.kwargs
        self.assertEqual(args['expected_sha'],'v1')
        nuevo=args['content_bytes']
        self.assertEqual(load_config(BytesIO(nuevo))[PARAMETRO_CAPACIDAD],1240)
        a=load_workbook(BytesIO(original));b=load_workbook(BytesIO(nuevo))
        for hoja in a.sheetnames:
            if hoja!='Configuración':self.assertEqual(list(a[hoja].values),list(b[hoja].values))
        github.download_file_bytes.return_value={'ok':True,'sha':'v2','content_bytes':nuevo}
        guardar_capacidad(github,nuevo,1300)
        final=github.upload_bytes_file.call_args.kwargs['content_bytes']
        ws=load_workbook(BytesIO(final))['Configuración']
        self.assertEqual(sum(row[0]==PARAMETRO_CAPACIDAD for row in ws.values),1)
        github.upload_bytes_file.reset_mock()
        with self.assertRaisesRegex(ValueError,'cambió'):guardar_capacidad(github,original,1400)
        github.upload_bytes_file.assert_not_called()
