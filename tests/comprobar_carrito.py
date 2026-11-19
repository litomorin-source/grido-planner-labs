from pathlib import Path
from io import BytesIO
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from openpyxl import load_workbook
from core.catalogo import resolver, HOJA
from ui.home import generar_carrito_importacion
p=Path(__file__).resolve().parents[1]/'data/Modelo_de_Carrito.xlsx'
assert resolver(p)['4000593']['precio']==13145.26
b,_,_=generar_carrito_importacion(pd.DataFrame([{'Código Compra':'4000857','Packs a Comprar':2}]),BytesIO(p.read_bytes()))
assert HOJA not in load_workbook(BytesIO(b)).sheetnames
print('OK: Delicia histórica y exportación sin metadatos internos.')
