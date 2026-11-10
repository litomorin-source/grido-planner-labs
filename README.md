# GridoPlanner Labs 2.5.0 — Control de capacidad de cámara

Esta es la versión de pruebas. **No subir a producción** hasta validar el funcionamiento.

## Nuevo
- Bultos actuales al cargar Stock, leyendo la columna `Bultos` de SmartFran **con signo**.
- Capacidad de referencia editable, inicial 980,98 bultos, calibrada contra el stock del 05/11/2026.
- Proyección a recepción: bultos stock − consumo estimado durante el tiempo de reposición + bultos del pedido.
- Consumo por producto a partir del motor de ventas existente, acotado por stock disponible, y convertido por Compra Mínima.
- Desglose de bultos por grupo y auditoría del consumo/compra por producto.
- Al generar Informe costo stock, registra también los bultos netos en el CSV histórico. Los registros anteriores permanecen con ese campo vacío.

## Alcance del conteo
Helado granel, Bombones, Familiares, Líneas especiales heladas, Palitos, Postres, Tentación, Tortas, Frizzio y Congelados Multimarca. No incluye Smoothie, GIO, insumos, descartables ni Gridos M. Prima. Este criterio coincide con 980,98 bultos netos del stock de referencia.

## Consideraciones
- Cada pack de compra del modelo de Carrito/Maestro se considera un bulto de recepción; corroborar con la definición logística del proveedor.
- La capacidad 980,98 es una **referencia operativa editable**, no un límite técnico certificado.
- Los artículos no clasificados no aportan consumo proyectado; se evita inventar su equivalencia.
- Para volver a calcular el pedido después de cambiar Mix o parámetros, presionar ANALIZAR Y GENERAR PEDIDO.

## Pruebas realizadas
- Validación de sintaxis de los scripts Python.
- Lectura del stock `Stock_20261105_105903.csv`: 980,98 netos; 1.039,22 positivos; −58,24 negativos.
- Prueba de motor con archivos de muestra y horizonte de 7 días: consumo estimado 153,76 bultos, 52 bultos de pedido, ocupación al recibir 879,22 (89,6 %). Son resultados de prueba, no una compra sugerida vigente.

Las descargas, el análisis de costos y la gestión de omisiones de Labs 2.4.0 permanecen en el código.
