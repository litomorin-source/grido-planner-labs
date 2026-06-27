# GridoPlanner Labs

## Versión

Labs 2.3.0

## Objetivo

Agregar historial y restauración del Maestro.

## Funcionalidad nueva

En Administrador → Actualizar archivos → Historial Maestro:

- Consulta últimos commits de `data/Maestro_Productos_Grido.xlsx`.
- Muestra fecha, mensaje, autor y SHA corto.
- Permite ver el commit en GitHub.
- Permite restaurar una versión anterior.
- Antes de restaurar:
  - descarga la versión histórica,
  - valida el Maestro,
  - compara contra la versión actual.
- La restauración crea un nuevo commit. No borra historial.

## Base

Deriva de Labs 2.2.0.
No modifica producción.
