# GridoPlanner Labs 3.0.3

Planificación semanal, costos de reposición y stock/cámara.

## Ejecutar

Instalar requirements.txt y ejecutar `streamlit run app.py`.
Configurar GITHUB_TOKEN, GITHUB_REPO y GITHUB_BRANCH en secrets de Streamlit.
No publicar secrets.toml.

## Datos operativos

- data/Maestro_Productos_Grido.xlsx: productos, presentaciones/alias, exclusiones y configuración.
- data/Modelo_de_Carrito.xlsx: catálogo vigente e historial interno _GP_Historial. Se conserva sin cambios en esta versión.
- data/Omisiones_Futuros_Pedidos.csv: archivo anterior, solo leído mientras haya omisiones pendientes de clasificar. La app ya no lo escribe; al completar la revisión queda ignorado. No borrarlo antes de terminar.
- data/Historial_Valorizaciones_Stock.csv: registros anteriores intactos; no se recalculan retroactivamente.

## Equivalencia única

Compra Mínima = presentaciones base por bulto. Unidades por presentación base = contenido de esa base.
Alias Unidad equivale a una unidad; alias Caja/pack usa Pack Detectado como unidades contenidas;
alias Presentación base equivale a una base. No leer gramos/litros como cantidad de unidades.
Unidades por bulto se deriva, no se almacena duplicado.
Crocante: 6 bases por bulto, 8 unidades por base. Alfajor: 6 y 6. Palitos: 10 y 10.
Productos cerrados: base individual, 1; caja sin TACC x12: 12 individuales, no una sola.
El motor aplica una única función a stock, ventas y tránsito. La cámara también calcula el físico con el Maestro.
Un dato conocido pero incompleto no se sustituye por Compra Mínima: se pide revisión.

## Estados de productos

Pedido → Administrar estados de productos permite cambiar uno o varios productos y seguir con otros sin regenerar entre guardados. Recalcular al terminar.

- Activo: participa normalmente.
- Discontinuado: compra cero, conserva equivalencias, stock físico, tránsito e historial. Las ventas siguen incluidas en costos. Puede volver a Activo.
- Excluido: fuera de pedidos, simulaciones, stock/cámara y costos. Para artículos ajenos de SmartFran o que todavía no se analizan, como velas.

La decisión vive en Estado de la hoja Productos. Para nombres sin ficha de producto (artículos excluidos de SmartFran), se usa Estado en la hoja Exclusiones, sin inventar código ni equivalencias. Los nombres se resuelven por sus aliases.
Los antiguos campos Activo/Excluir son compatibles con maestros anteriores y se sincronizan al guardar desde la interfaz; cuando existe Estado, este es la autoridad. No editar esos campos antiguos para cambiar un Estado: usar la interfaz o la columna Estado.
No se infiere discontinuación por ausencia en el Carrito.

En la primera actualización se muestran las omisiones anteriores pendientes. Cada una conserva su efecto anterior hasta clasificarla. No se presume que todas son discontinuadas ni que todas son exclusiones generales. Al completar la revisión se registra en Configuración y deja de consultarse el CSV externo, que queda como respaldo. No hay un botón separado de migración.
Un nombre sin ficha no puede marcarse Discontinuado hasta completar sus equivalencias; sí puede Excluirse o volver a Activo para revisarlo.
Los guardados verifican el SHA del Maestro; si otra persona lo modificó, se pide recargar para evitar pisar cambios.

## Productos nuevos

Stock y cámara → Completar productos. Confirmar bases por bulto, unidades por base y presentación
de cada nombre. La vista previa muestra el factor; se guarda una sola definición en el Maestro.
También se puede revisar un producto existente desde ese mismo panel. Si cambia el contenido del
pack, revisar la equivalencia; cambios de precio no modifican estos datos.

## Capacidad

La referencia 980,98 proviene de un stock anterior expresado en bultos SmartFran, no de una medición.
Debe revisarse bajo el nuevo criterio. Bultos de packs diferentes tampoco son una medición en m³.
Los registros históricos de cámara conservan su criterio original.

## Pruebas

`python -m unittest discover -s tests -v`
Las pruebas que requieren informes privados se habilitan con GRIDO_DATOS_PRUEBA.
No escriben en GitHub. El adaptador tests/app_interfaz_local.py permite comprobar la UI con guardados en memoria.

## Criterio de desarrollo

Una fuente por dato y una regla compartida. Historial conservado. Las tareas excepcionales se resuelven
internamente; no se agregan botones permanentes para migraciones de una sola vez.

## Corrección 3.0.1

La cantidad sugerida depende del stock, ventas, semanas configuradas y equivalencias del Maestro. Las restricciones del Carrito (disponibilidad, máximos, mínimos y múltiplos) solo generan advertencias. Un código ausente, precio pendiente o presentación para revisar no reduce la cantidad a cero. Los cambios de nombre por sí solos no bloquean ni descartan un costo histórico. Los cambios físicos de peso/cubicaje siguen marcados para revisar; no se modifican equivalencias automáticamente.

El archivo de importación al proveedor requiere que sus códigos existan en la plantilla: si faltan, se informa el problema sin quitar productos del informe de pedido.

## Correcciones 3.0.2

Formato monetario compartido para los Excel de Pedido, Stock y Carrito de importación. La capacidad de cámara se guarda desde Stock y cámara en Configuración del Maestro con control de versión. Las omisiones permiten selección múltiple o sucesiva sin perder candidatos; las descargas anteriores se invalidan y se recalcula al terminar. No cambian las fórmulas de compra.

## Correcciones 3.0.3

Estados unificados en el Maestro y revisión de omisiones anteriores. Se retira el cartel de omitidos en Costos. Selectores de estados con texto en español. Detalle de costos y productos sin cobertura se descargan en Excel, con importes numéricos y formato $.
Las advertencias de referencias históricas de stock/cámara solo consideran productos con stock o tránsito distinto de cero (se comprueban separados, incluso si se compensan). En Costos permanecen para ventas que usan referencias históricas. No se borra el historial.

La fórmula de pedido para productos activos no cambia. Se preservan las advertencias del Carrito sin aplicar mínimos, máximos ni disponibilidad a las cantidades. Pallets queda pendiente.

Pruebas adicionales: `GRIDO_DATOS_PRUEBA=/carpeta PYTHONPATH=. python tests/comprobar_estados_303.py` y `python tests/comprobar_bugs_302.py` con el mismo entorno. El archivo de datos de prueba no se distribuye.
