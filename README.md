# GridoPlanner Labs

## Versión

Labs 2.2.0

## Objetivo

Agregar control de cambios del Maestro antes de guardarlo en GitHub.

## Funcionalidad nueva

Cuando el administrador sube un Maestro nuevo:

- Se valida estructura.
- Se descarga el Maestro vigente desde GitHub.
- Se comparan productos.
- Se muestran:
  - productos agregados,
  - productos eliminados,
  - cambios en código de compra,
  - cambios en producto compra,
  - cambios en compra mínima,
  - cambios en activo,
  - cambios en excluir,
  - cambios en tipo producto.
- Si hay productos eliminados, exige confirmación explícita antes de guardar.

## Base

Deriva de Labs 2.1.1.
No modifica producción.
