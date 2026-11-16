# GridoPlanner Labs 2.7.0 — Interfaz compacta

## Instalación

Este ZIP actualiza el repositorio Labs existente. No es una aplicación completa.
Extraerlo y subir los archivos a la raíz del repositorio LABS, conservando sus
carpetas: `ui`, `core`, `tests` y `.streamlit`. Mantener `app.py` como entrada.
También debe subirse `.streamlit/config.toml`, que define la paleta de colores.
Si ya existe una configuración propia, incorporar solo el bloque `[theme]`.
No reemplazar Maestro, Carrito, omisiones, historial ni secretos: no se incluyen.
El paquete está preparado y probado localmente; no está desplegado en Streamlit Cloud.

## Mejoras visuales

- Un encabezado compacto con nombre y versión, sin títulos repetidos.
- Navegación lateral: Pedido, Stock y cámara, Costos, Configuración y Pallets.
- Carga plegable: se cierra al completar los tres archivos y se puede volver a abrir.
- Cuatro indicadores destacados: importe, packs, ocupación estimada y productos para revisar.
- Descargas junto al resumen; botón principal para generar el pedido.
- Tabla principal de compra más corta; diagnóstico, simulador y datos completos en desplegables.
- Historial con tabla resumida y un gráfico seleccionable por métrica y período.
- Paleta azul, fondo suave y jerarquía visual más clara.

La navegación conserva los controles y las descargas de la sesión. Los paneles
permanecen montados, como las pestañas anteriores, y solo se muestra el seleccionado.
Cambiar de sección no ejecuta nuevamente el motor del pedido.
El optimizador de pallets sigue siendo un apartado pendiente, sin cálculo nuevo.

## Correcciones anteriores incluidas

- Omisiones compartidas entre Pedidos y Costos del mix, incluida la cobertura.
- Bultos visibles como enteros; cálculo interno con precisión completa.
- Llegada estimada editable, con miércoles de la semana siguiente como referencia.
- Invalidación de resultados al modificar archivos, parámetros, Maestro, Carrito u omisiones.
- Precios desconocidos identificados y valorizaciones incompletas como subtotales.
- Cámara con stock físico, tránsito y nueva compra; consumo limitado a existencias físicas.

## Validación

Se aprobaron 16 pruebas de regresión con los informes recibidos el 16/11/2026.
Con 4 semanas objetivo, 1 de reposición y 14 días de ventas, se conservan
185 packs y $5.007.851, con las mismas cantidades por producto que el pedido de referencia.

También se ejecutó la interfaz con Streamlit AppTest: pantalla vacía, datos cargados,
generación, navegación por las cinco secciones, conservación de archivos descargables,
selección de gráficos, cálculo de costos, invalidación por cambio de parámetros y limpieza.
Las pruebas usan archivos locales y no escriben en GitHub. AppTest verifica ejecución
y estado; queda pendiente comprobar el aspecto final en el navegador de Streamlit Cloud.

Para repetirlas desde la raíz del repositorio, con dependencias instaladas:

```bash
GRIDO_DATOS_PRUEBA=/carpeta/informes python -m unittest discover -s tests -v
GRIDO_DATOS_PRUEBA=/carpeta/informes python tests/comprobar_interfaz.py
```

Ejecutarlas en procesos separados. La segunda requiere los informes privados de referencia
y los archivos de `data` del repositorio original, incluido el historial de stock.

Después de actualizar, comprobar que la cabecera diga Labs 2.7.0, cargar los tres
informes, generar y recorrer las secciones. Los datos completos siguen en desplegables.
