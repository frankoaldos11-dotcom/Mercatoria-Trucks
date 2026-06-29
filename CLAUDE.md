# CLAUDE.md — Mercatoria Truck

## PLAN MODE — MERCATORIA TRUCK

Antes de implementar cualquier cambio en este proyecto, siempre:

1. Inspecciona los archivos afectados
2. Presenta un plan en formato de tabla con: qué se cambia, complejidad (baja/media/alta) y archivos afectados
3. Espera aprobación explícita de Aldo antes de escribir una sola línea de código
4. Solo después de recibir "aprobado" o "dale" procedes con la implementación

Esta regla aplica a todos los prompts, sin excepción. Si el prompt dice "implementa X", igual presentas el plan primero.

La única excepción es cuando el prompt dice explícitamente "sin plan, implementa directo".

## PLAYWRIGHT POST-COMMIT — REGLA PERMANENTE

Después de cada commit en este proyecto, sin excepción:

1. Lanza Playwright y navega todas las páginas afectadas por los cambios del commit
2. Toma screenshots de cada página visitada
3. Captura errores de consola (nivel error/warning) y errores HTTP (4xx, 5xx)
4. Genera o actualiza `test_report.md` en la raíz del proyecto con la estructura estándar (fecha, páginas probadas, errores, screenshots, correcciones, recomendaciones)

Esta regla aplica a todos los commits, incluso si el cambio parece trivial. Si Playwright no está disponible, indicarlo explícitamente al usuario antes de continuar.
