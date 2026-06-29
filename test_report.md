# Reporte de Pruebas — 2026-06-28

## Páginas probadas
- http://127.0.0.1:5000/login
- http://127.0.0.1:5000/admin/ (dashboard)
- http://127.0.0.1:5000/admin/viajes
- http://127.0.0.1:5000/admin/viaje/2 (gestionar_viaje — nuevo flujo secuencial)
- http://127.0.0.1:5000/admin/viajes/2/gestionar (alias — misma vista)
- http://127.0.0.1:5000/admin/incidencias (nueva vista)
- http://127.0.0.1:5000/admin/configuracion

## Errores encontrados
Ninguno. Todas las páginas devolvieron HTTP 200. Sin errores de consola ni warnings.

## Screenshots tomados
- `test_admin_dashboard.png` — dashboard admin con cartel informativo
- `test_gestionar_viaje.png` — nueva vista de viaje con pasos secuenciales
- `test_incidencias.png` — nueva vista global de incidencias
- `test_configuracion.png` — configuración financiera

## Correcciones aplicadas

### Change 1 — Flujo de viaje rediseñado
`templates/admin/gestionar_viaje.html` reescrito completamente. Eliminadas las pestañas y el checklist separado. Reemplazado por 8 tarjetas de pasos secuenciales:
1. Asignar camionero y vehículo
2. Confirmar precio cliente
3. Confirmar combustible asignado
4. Fecha de extracción
5. Fecha de descarga
6. Enviar documentación (toggle AJAX sobre checklist)
7. Confirmar entrega
8. Cerrar operación (pago camionero — solo admin)

Los pasos completados se muestran colapsados en verde. El panel de info (cliente, ruta, camionero, precios, fechas) siempre visible arriba. Los detalles adicionales (liquidación, pago, prioridad, documentos, WhatsApp, notas, incidencias) en acordeones `<details>` al fondo.

### Change 2 — Campos numéricos sin flechitas
- `templates/cliente/solicitar.html`: `cantidad_contenedores` → `type="text" pattern="[0-9]*" inputmode="numeric"`
- `templates/admin/configuracion.html`: CSS `-moz-appearance:textfield` + `-webkit-appearance:none` para ocultar spinners en todos los `.config-input`

### Change 3 — Bug configuración no guarda
- `services/finanzas_service.py`: `guardar_configuracion` reescrito con UPSERT (`ON CONFLICT(clave) DO UPDATE`) en lugar de `UPDATE` (que no inserta si la fila no existe)
- `routes/finanzas.py`: `configuracion_texto` INSERT reescrito con UPSERT compatible con PostgreSQL y SQLite, usando `USE_POSTGRES` para seleccionar placeholder

### Change 4 — Mensaje km mínimo
`templates/admin/gestionar_viaje.html`: Mensaje reescrito a "Se aplica el mínimo de X km para esta liquidación porque la ruta tiene menos km registrados (Y km reales)."

### Change 5 — Logo roto en móvil
`templates/admin/base_admin.html`: SVG inline con `style="display:block;flex-shrink:0;"`, tamaño 24×24. Texto con `style="color:#fff;font-weight:700;font-size:15px;white-space:nowrap;"`.

### Change 6 — Incidencias
- `routes/admin.py`: Nueva ruta `GET /admin/incidencias` con filtros por estado y categoría
- `templates/admin/incidencias.html`: Nueva vista con tabla, filtros por select, cambio de estado AJAX sin recarga
- `templates/admin/base_admin.html`: Enlace "Incidencias" añadido al sidebar bajo SISTEMA (solo admin)

### Change 7 — Cartel informativo en dashboard
`templates/admin/dashboard.html`: Bloque azul admin-only listando secciones exclusivas del administrador.

## Recomendaciones
- Probar el flujo completo de viaje creando un viaje nuevo y avanzando cada paso en orden
- Verificar en producción (Render + PostgreSQL) que los UPSERT de configuración persisten correctamente
- El paso 6 (Documentación enviada) usa toggle AJAX sobre `viaje_checklist`; verificar que el item "Documentación enviada" esté en `CHECKLIST_ITEMS_DEFAULT` y se cree automáticamente al crear un viaje
- Considerar añadir validación backend para que el paso 7 (estado → Entregado) solo sea posible si los pasos 1–5 están completados
