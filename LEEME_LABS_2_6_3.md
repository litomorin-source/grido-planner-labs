# GridoPlanner Labs 2.6.3 — Actualización de confiabilidad

Paquete de actualización para el repositorio Labs recibido el 16/11/2026.
Extraer el ZIP y subir su contenido a la raíz del repositorio LABS, conservando
las carpetas `core`, `ui` y `tests`. Mantener `app.py` como punto de entrada.
Este paquete contiene únicamente archivos de código modificados, pruebas y esta nota.
No contiene reemplazos de Maestro, Carrito, omisiones, historial ni secretos.
No es una aplicación completa para instalar en un repositorio vacío.

## Cambios

- Los resultados y descargas se invalidan cuando cambian archivos, parámetros,
  Maestro, Carrito u omisiones. Se requiere analizar nuevamente.
- Los precios ausentes o no positivos quedan vacíos, con detalle en la hoja
  `Sin precio`. Las valorizaciones incompletas se identifican como subtotales.
- El historial de stock conserva los registros anteriores y agrega una columna
  de valorización completa. Los registros anteriores quedan como `Sin verificar`.
- La cámara separa existencias físicas, tránsito y nueva compra. Una casilla
  permite indicar si el tránsito llega antes o junto con el pedido nuevo.
- El tránsito se calcula desde el stock y el Maestro original, independientemente
  de las omisiones de compra. Una omisión no hace desaparecer mercadería pendiente.
- El consumo previsto se limita al stock físico positivo por producto.
  No se anticipa consumo de entregas pendientes: es una proyección prudente,
  que puede sobreestimar ocupación si esas entregas llegan temprano y se venden.
- Los productos sin equivalencia se muestran pendientes. No se afirma que haya
  espacio suficiente cuando hay tránsito que no se puede convertir.
- Los tres escenarios conservan los días reales del informe de ventas;
  se siguen comparando semanas objetivo y tiempo de reposición.
- Versión de interfaz unificada en `core/version.py`.

## Comprobación con los archivos recibidos

Stock_20261116_124624.csv; Cajas por Sabor (43).xlsx;
Kilos y Cantidades por Período (10).xlsx; Pedido_Final (42).xlsx.
Maestro y Carrito: copias de la carpeta `data` del ZIP original.

Parámetros del pedido de referencia: 4 semanas objetivo, 1 semana de reposición,
14 días analizados. Se reproducen 185 packs y $5.007.851 de compra sugerida.
Todas las líneas con compra tienen precio en este ejemplo.

El pedido de referencia contiene 97 filas. El maestro sin omisiones genera 100;
con las cinco omisiones actualmente guardadas en el ZIP, genera 95. Las diferencias
son artículos sin compra; las cantidades a comprar y el importe coinciden.

Precios pendientes con existencias: Crema al Cielo y Palito Frutal Limón.
No se asignaron precios ni equivalencias inventadas.

### Cámara: escenario condicional, no una orden de compra

Si todo el tránsito pendiente llega antes o junto con el pedido nuevo:

| Concepto | Bultos |
| --- | ---: |
| Físicos actuales, según CSV | 659,71 |
| Consumo descontado, limitado al físico | -225,20 |
| Tránsito con conversión conocida | +628,18 |
| Nueva compra | +185,00 |
| Ocupación proyectada conocida | 1.247,70 |
| Capacidad de referencia editable | 980,98 |

La ocupación conocida estimada equivale al 127,2% de la referencia.
Además hay 7 unidades en tránsito de Crema al Cielo sin equivalencia de compra
en este maestro; el cálculo de bultos queda incompleto.
La cámara usa equivalencias operativas de bultos, no volumen físico certificado.
Confirmar fechas de recepción y equivalencias antes de usar este cálculo para decidir.

La proyección anterior, con este pedido y sin sumar tránsito, era de 589,56 bultos
(60,1%). También permitía descontar consumo de mercadería que todavía no estaba físicamente.

## Validación

11 pruebas locales aprobadas: reproducción de cantidades, precios desconocidos,
subtotales incompletos, stock valorizado, tránsito, consumo limitado al físico,
omisiones, cambios de insumos, detección de archivos y carrito importable
(códigos como texto, cantidades enteras).

Las pruebas no llaman ni escriben en GitHub. La importación de funciones puras de
la interfaz usa adaptadores para Streamlit y requests; no sustituye una prueba
visual o de navegación. Se comprobó también sintaxis de los archivos modificados.
Pendiente: validación visual en Streamlit Cloud y confirmación del calendario de tránsito.

Para repetir pruebas en el repositorio con las dependencias instaladas:

    GRIDO_DATOS_PRUEBA=/carpeta/con/los/cuatro/archivos python -m unittest discover -s tests -v

Sin esa variable se ejecutan las pruebas que no requieren datos privados.

## Revisión en Labs

1. Cargar los tres informes y seleccionar 4 / 1 / 14.
2. Generar y comprobar 185 packs y $5.007.851 con el Maestro/Carrito de referencia.
3. Cambiar semanas objetivo y comprobar que desaparezcan las descargas anteriores.
4. Regenerar y revisar los productos sin precio y la casilla del tránsito.
5. Descargar el carrito y comprobar que mantenga las cantidades y códigos.

El optimizador de pallets continúa pendiente para una etapa posterior.
