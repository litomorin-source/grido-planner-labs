# GridoPlanner Labs 3.0.0

Planificación semanal, costos de reposición y stock/cámara.

## Ejecutar

Instalar requirements.txt y ejecutar `streamlit run app.py`.
Configurar GITHUB_TOKEN, GITHUB_REPO y GITHUB_BRANCH en secrets de Streamlit.
No publicar secrets.toml.

## Datos operativos

- data/Maestro_Productos_Grido.xlsx: productos, presentaciones/alias, exclusiones y configuración.
- data/Modelo_de_Carrito.xlsx: catálogo vigente e historial interno _GP_Historial. Se conserva sin cambios en esta versión.
- data/Omisiones_Futuros_Pedidos.csv: omisiones de Pedido/Costos; no quitan mercadería física de Cámara.
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

## Exclusiones

La hoja Exclusiones, Excluir=Sí y Activo=No se propagan a todos los alias y a todas las secciones.
Las omisiones guardadas de Pedidos conservan el comportamiento anterior: excluyen Pedido/Costos,
pero mantienen el stock físico. No se migran silenciosamente de una categoría a otra.

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
