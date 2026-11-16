# GridoPlanner Labs 2.8.0 — Completar productos desde Stock y cámara

## Instalación

Actualización acumulativa para el repositorio Labs existente. Extraer el ZIP y
subir su contenido a la raíz de LABS, conservando `ui`, `core`, `tests` y `.streamlit`.
Mantener `app.py` como punto de entrada. No es un repositorio completo.
Se incluyen archivos nuevos: `core/alta_productos.py` y `ui/productos.py`.
También cambia `core/github_sync.py` para controlar la versión al guardar.
Si ya existe una configuración propia en `.streamlit/config.toml`, incorporar
solo el bloque de tema. No reemplazar los datos ni los secretos del repositorio.
Esta entrega no está desplegada y no modificó el Maestro real.

## Uso

1. Cargar Stock y entrar en **Stock y cámara**.
2. Abrir **Completar productos del stock**, donde aparece la cantidad de pendientes.
3. Elegir el producto y buscar su artículo en el Carrito por nombre o código.
4. Confirmar tipo, presentaciones base por bulto y peso del bulto en kg.
5. Para nombres nuevos de Stock, indicar cómo se expresa su cantidad.
6. Revisar la comparación de datos y las conversiones mostradas.
7. Ingresar el PIN habitual de administrador y pulsar **Guardar producto en el Maestro**.
8. Regenerar los informes de Stock, Pedido y Costos para usar los nuevos datos.

El panel detecta fichas faltantes, códigos ausentes o sin precio vigente y
equivalencias vacías/no positivas. Ordena el catálogo por parecido del nombre,
pero la vinculación requiere elegir explícitamente el artículo.
Si un producto no aparece en el Carrito, primero hay que actualizar ese archivo
desde Administración → Actualizar archivos. No se inventan precios ni códigos.

## Datos de compra y conversiones

El precio continúa leyendo el Carrito vigente por código; no se copia como un
precio fijo al Maestro. El valor del stock se deriva de ese precio y la equivalencia.
El peso se propone desde el Carrito, se confirma y se registra en `Peso Compra (kg)`.
El contenido del bulto se confirma manualmente: `minimo`, `multiplo` y `Cubicaje`
del Carrito no son unidades por caja y no se usan como sustitutos.
En palitos la presentación base del motor es x10: x20 equivale a dos bases,
y la unidad suelta se divide por diez. Las conversiones se muestran antes de guardar.
Para otras presentaciones no compatibles, el panel pide revisar los datos.

## Alcance del guardado

- Agrega o actualiza la ficha del producto elegido en Productos.
- Agrega los nombres nuevos de Stock a Aliases.
- Conserva los alias existentes, incluso repeticiones coherentes por origen.
- Bloquea códigos asignados a otro producto, alias contradictorios y reactivaciones implícitas.
- Conserva las demás hojas, fórmulas, omisiones e historial; no reescribe registros históricos.
- Comprueba nuevamente Maestro y Carrito antes de guardar y envía el SHA esperado
  del Maestro a GitHub para no pisar cambios simultáneos en ese archivo.
- Cada guardado queda en el historial de commits del Maestro.
- Invalida resultados anteriores para que se regeneren con los datos nuevos.

## Casos comprobados con los archivos recibidos

Palito Frutal Limón figura en el Maestro con código 4000139. El Carrito recibido
contiene 4000857, PACK 10 CAJ. GRIDO FRUTAL LIMON X 10 UN, precio $13.643,23.
La prueba local seleccionó ese artículo y confirmó 10 presentaciones por bulto.
El producto dejó de aparecer como pendiente y obtuvo valorización.
No se aplicó esta selección automáticamente al archivo real.

Crema al Cielo no figura en el Carrito recibido. El alta se probó con un artículo
ficticio agregado exclusivamente a una copia temporal de prueba. Para completarlo
en la app hace falta un Carrito que incluya el código y precio reales.

## Comprobaciones

23 pruebas de regresión aprobadas: las 16 anteriores más 7 del editor y guardado.
El pedido de referencia sin modificar el Maestro conserva 185 packs y $5.007.851.
AppTest verificó navegación, descargas, gráficos, costos, invalidación y limpieza.
También verificó selección de artículo, vista previa, bloqueo por PIN, guardado
en memoria, recarga del Maestro y desaparición del pendiente corregido.
Las pruebas no escriben en GitHub. Queda pendiente revisar el aspecto final
y el guardado con la conexión real después de subir esta versión a Labs.

Con las dependencias instaladas, desde la raíz del repositorio y en procesos separados:

```bash
GRIDO_DATOS_PRUEBA=/carpeta/informes python -m unittest discover -s tests -v
GRIDO_DATOS_PRUEBA=/carpeta/informes python tests/comprobar_interfaz.py
GRIDO_DATOS_PRUEBA=/carpeta/informes python tests/comprobar_editor.py
```

Los casos de referencia requieren los datos originales del repositorio y los
informes recibidos el 16/11/2026, que no se incluyen en este paquete.

## Mejoras anteriores incluidas

Detalle del pedido contraído por defecto, navegación lateral, carga plegable,
resumen destacado, historial compacto, omisiones compartidas con Costos,
bultos visibles sin decimales, fecha estimada editable y cálculos prudentes de cámara.
El optimizador de pallets sigue pendiente.
