# Reporte de Pruebas — 2026-06-29

## Páginas probadas
- `http://127.0.0.1:5000/login` — Login como admin (user: admin / 1234)
- `http://127.0.0.1:5000/admin/comercial/rutas` — Formulario Nueva ruta (item 1)
- `http://127.0.0.1:5000/admin/configuracion?tab=tab-rutas` — Pestaña Rutas KM (item 2)
- `http://127.0.0.1:5000/admin/reportes` — Columna Verificado (item 3)
- `http://127.0.0.1:5000/admin/comercial/cotizar` — Dropdown tipo vehículo (item 4)

## Errores encontrados
- Sin errores de consola JavaScript.
- Sin errores HTTP (4xx / 5xx).

## Screenshots tomados
- `ss_8983l8waw` — Rutas: formulario sin campo Tarifa/km visible
- `ss_2003mrbcm` — Configuración: pestaña "Rutas — KM" activa con tabla de rutas
- `ss_2395odjum` — Reportes: tabla de viajes del período
- `ss_0108cdjm3` — Cotizar: formulario con dropdown Tipo de vehículo

## Correcciones verificadas en esta sesión (Prompt G)

| # | Verificación | Estado | Evidencia |
|---|---|---|---|
| 1 | Campo "Tarifa/km (auto)" oculto en Nueva ruta — solo visible Origen, Destino, Zona, KM | ✅ | `ss_8983l8waw` |
| 2 | Pestaña "Rutas — KM" en /admin/configuracion con 3 rutas y botones "Editar km" | ✅ | `ss_2003mrbcm` |
| 3 | Columna "VERIFICADO" en /admin/reportes con botón "Confirmar cobrado y verificado" | ✅ | scroll screenshot |
| 4 | Dropdown "Tipo de vehículo" en /admin/comercial/cotizar carga 10 opciones de `tipos_vehiculo` | ✅ | JS inspect |
| — | Sin errores de consola en ninguna página | ✅ | read_console_messages |
| — | Migración DB: columnas verificado_financiero/verificado_por/fecha_verificacion añadidas | ✅ | agregar_columna en database.py |

## Recomendaciones
- El botón "Confirmar cobrado y verificado" aparece en todos los viajes (cobrados o no). Si se prefiere restringirlo solo a viajes ya cobrados, se puede añadir `{% if f.cobrado %}` como condición adicional.
- El tab "Rutas — KM" en Configuración muestra la zona en minúsculas para algunas rutas (ej: "occidente") — puede normalizarse en el UPDATE de `editar_ruta`.
- El dropdown de cotizar ahora usa `tipos_vehiculo`; si se quiere calcular precios automáticamente, se debe revisar que existan tarifas en la tabla `tarifas` para los IDs de `tipos_vehiculo` correspondientes.
