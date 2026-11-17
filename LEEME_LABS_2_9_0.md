# GridoPlanner Labs 2.9.0 — Carritos e historial de referencias

## Instalar

Actualización acumulativa para el repositorio LABS existente. Extraer y subir
los archivos conservando las carpetas `core`, `ui`, `tests`, `.streamlit` y `respaldo`.
Mantener `app.py` como entrada. No es un repositorio completo para instalar de cero.
Si hay configuración propia en `.streamlit/config.toml`, incorporar solo el tema.
No se incluyen reemplazos de Maestro, Carrito operativo, omisiones, historial de stock
ni secretos. El archivo de `respaldo` es una referencia separada que solo se usa
cuando se elige recuperarla desde la interfaz.

El paquete está preparado y probado localmente; no se desplegó en Streamlit Cloud
y no se escribieron datos reales en GitHub.

## Resolver Delicia sin volver a un Carrito viejo

1. Entrar como Administrador e ingresar el PIN habitual.
2. Ir a Actualizar archivos → Actualizar Carrito.
3. Elegir **Recuperar datos de un Carrito anterior**.
4. Marcar **Usar el Carrito de referencia recuperado del ZIP original (incluye Delicia)**.
5. Si se conoce la fecha comercial del archivo, informarla. Si no, dejarla vacía.
6. Revisar los datos recuperados, marcar la casilla de revisión y guardar el respaldo.
7. Volver a planificación y regenerar Stock y Costos.

Se recuperó del ZIP original el código 4000593, PACK 4 U DELICIA DE CHOCO.Y MANÍ - GRIDO:
precio de referencia $13.145,26, cubicaje 0,513 y peso 2,4 kg. La fecha comercial
no está informada en ese archivo; no se inventa una fecha de vigencia.
El Maestro actualizado que enviaste ya tiene correctamente esa asociación.
La recuperación conserva intactas las filas del Carrito vigente y el Maestro,
incluida tu asociación de Palito Frutal Limón, código 4000857, pack de 10 cajas x10.
El respaldo puede aportar datos de otros artículos ausentes, además de Delicia;
la pantalla muestra cuáles antes de guardar.

## Actualizar Carrito en adelante

Seleccionar **Actualizar Carrito vigente**, subir el nuevo archivo, indicar su fecha
si se conoce y revisar la comparación. Muestra artículos nuevos, ausentes y que
reaparecen; diferencias de precio, descripción, peso, cubicaje, IVA, depósitos,
disponibilidad, mínimo, máximo y múltiplo. Se ven los valores anteriores y nuevos.
Las variaciones de precio del 20% o más y la desaparición de más del 20% del catálogo
generan advertencias adicionales. También se avisa si se declara una fecha anterior
a un Carrito guardado. Las cargas requieren revisar la comparación antes de guardar.

Un artículo ausente conserva sus datos anteriores y su asociación. La ausencia
no significa automáticamente que esté discontinuado. Si reaparece, se reconoce
por código. Los códigos nuevos no se vinculan automáticamente por parecido de nombre.
Las filas con códigos duplicados se bloquean para revisar; no se elige una al azar.

## Precio, peso y cubicaje históricos

Se usa el dato actual válido. Cuando falta o es inválido, se busca el último dato
compatible conocido de la misma presentación. Los valores cero, vacíos o negativos
de precio/peso/cubicaje no borran un dato válido anterior.
Cada referencia conserva archivo, fecha comercial declarada y momento de incorporación.
Una importación histórica no reemplaza valores válidos del catálogo vigente.
Entre respaldos importados con fecha conocida se prioriza el más reciente; los
datos observados en Carritos vigentes guardados tienen prioridad sobre importaciones.
Los datos sin fecha se identifican como tales y no se presentan como vigentes.

Los precios se conservan con su precisión de origen. Los cálculos del motor mantienen
el criterio de redondeo en pesos que ya utilizaba la aplicación.

Los cambios de descripción, peso o cubicaje se tratan como posibles cambios de
presentación. Conservan la referencia anterior y bloquean la compra de ese código
hasta revisar. Si solo es una corrección de datos y sigue siendo la misma presentación
física, se puede confirmar expresamente al cargar el Carrito. Si realmente cambió
el contenido del pack, hay que reconciliar Maestro y existencias; no se convierte
automáticamente el stock viejo ni se mezclan equivalencias de dos presentaciones.
Un histórico incompatible con la descripción/peso del Maestro no se usa para valorizar.

## Stock, cámara y Costos

Stock y cámara muestra las referencias y fechas, con advertencia para datos históricos
o pendientes. Un producto valorizado con respaldo deja de ser una asociación obligatoria
pendiente. Si se necesita cambiar realmente su código, la opción **También quiero revisar
asociaciones con costo histórico** permite abrirlo voluntariamente en el editor.

Los informes de Stock y Pedido agregan origen del precio, fecha, estado del catálogo,
cubicaje de referencia y la hoja **Referencias catálogo**. El historial de valorizaciones
marca los registros nuevos que usan costos históricos; no recalcula registros anteriores.
Costos del mix identifica las referencias históricas: son últimos costos conocidos,
no precios actuales de reposición ni costo contable de las ventas.

El cubicaje se conserva y puede consultarse por producto. Los bultos físicos de cámara
siguen leyendo el stock de SmartFran y las equivalencias del Maestro. No se convierte
el cubicaje del proveedor en bultos físicos ni se sustituye la capacidad de referencia.
El optimizador de pallets sigue pendiente.

## Reposición y restricciones

Los códigos ausentes, con precio actual inválido o con cambios de presentación
pendientes no se compran automáticamente. Conservan su necesidad de reposición
y muestran el motivo para revisar.
Se aplican mínimo y múltiplo enteros del Carrito, respetando máximo y disponibilidad
informados en ese archivo. Si no alcanza para el mínimo o la disponibilidad es cero,
la compra queda en cero con advertencia. No representa disponibilidad consultada en vivo:
conviene cargar un Carrito actualizado antes de comprar.

Este cambio puede modificar las cantidades sugeridas respecto de versiones anteriores.
En el caso de prueba original (4/1/14), Frutal Frutilla tiene Disponible=0:
se retiran sus 9 packs y el total pasa de 185 packs / $5.007.851 a
176 packs / $4.885.064. Las demás líneas de compra coinciden con la referencia.
Este resultado corresponde a los archivos de prueba originales, no a una compra nueva.

## Conservación del historial

Los datos históricos se guardan en una hoja interna del mismo Carrito operativo,
conservando la primera hoja del proveedor. Un solo guardado con control de versión
publica catálogo e historial juntos; un cambio simultáneo en GitHub bloquea el guardado.
Las exportaciones para importar pedidos eliminan esa hoja interna y mantienen las
columnas del proveedor, códigos como texto y cantidades enteras.

Actualizar siempre desde esta pantalla. Reemplazar el archivo directamente en GitHub
con un Carrito sin la hoja interna elimina el respaldo de ese archivo operativo.
El historial de commits de GitHub conserva las versiones anteriores para recuperarlas.

## Validación

34 pruebas aprobadas: regresión previa más historial, recuperación, reapariciones,
datos inválidos, fechas, presentaciones incompatibles, duplicados, restricciones y
conflictos de guardado. Comprobación real con el Maestro (4) y Carrito (29) recibidos.
AppTest verificó navegación, generación, descargas, gráficos, Costos, editor de productos,
modo Administrador y recuperación de Delicia con guardado simulado en memoria.
El Carrito actual y el Maestro del usuario permanecen iguales durante la recuperación.
Queda pendiente comprobar aspecto y guardado con la conexión real después de instalar.

Para repetir pruebas, con dependencias del proyecto instaladas, en procesos separados:

```bash
GRIDO_DATOS_PRUEBA=/carpeta/informes python -m unittest discover -s tests -v
GRIDO_DATOS_PRUEBA=/carpeta/informes python tests/comprobar_interfaz.py
GRIDO_DATOS_PRUEBA=/carpeta/informes python tests/comprobar_editor.py
python tests/comprobar_modos.py
```

Para la recuperación con archivos nuevos, agregar las variables `GRIDO_CARRITO_NUEVO`
y `GRIDO_MAESTRO_NUEVO` con las rutas de los archivos (29) y (4). Luego ejecutar
las pruebas unitarias y `python tests/comprobar_carrito.py` con esas variables y
`GRIDO_DATOS_PRUEBA`. Los informes privados de prueba no se incluyen en el ZIP.
