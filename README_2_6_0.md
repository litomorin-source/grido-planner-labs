# GridoPlanner Labs 2.6.0 — Interfaz y carga inteligente

Actualización de Labs 2.5.0. **No instalar en producción.**

## Cambios

- Cargador único: acepta Stock CSV, Cajas por Sabor XLSX y Mix de Ventas XLSX, juntos o por separado.
- Identificación por columnas/contenido, no por nombre de archivo.
- Persistencia de archivos en sesión al cambiar de pestaña, descargar o ejecutar un informe.
- El reemplazo de un archivo requiere confirmación; el resto permanece intacto.
- Limpieza completa de archivos y resultados con un botón.
- Secciones de Usuario: Pedido, Pallets, Stock y cámara, Costos, Configuración.
- Stock y cámara pueden consultarse con Stock únicamente. Los informes de pedidos y costos exigen los tres archivos.
- Se mantienen los formatos y descargas del pedido de Labs 2.5.0.
- La pestaña Pallets es por ahora informativa: el optimizador se implementará y validará aparte.

## Instalación

Actualizar el código de `ui/home.py` y `core/version.py` dentro del repositorio Labs. No cambiar `data/`, archivos de Maestro/Carrito ni secretos. Requiere la estructura restante de Labs 2.5.0, especialmente `core/capacidad_camara.py`.

## Pruebas

- Detección con Stock_20261105_105903.csv, Cajas por Sabor (12).xlsx, Kilos y Cantidades por Período.xlsx.
- Persistencia de carga parcial y confirmación de reemplazo.
- Compilación sintáctica de todos los archivos de Python.

Pendiente de validar visualmente en Streamlit Cloud.
