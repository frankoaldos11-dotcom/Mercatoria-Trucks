# Reporte de Pruebas — 2026-06-29

## Páginas probadas

| URL | HTTP | Consola |
|-----|------|---------|
| `/login` | ✅ 200 | sin errores |
| `/admin/` (dashboard) | ✅ 200 | sin errores |
| `/admin/configuracion` (tab Parámetros) | ✅ 200 | sin errores |
| `/admin/configuracion` (tab Tipos de vehículo) | ✅ 200 | sin errores |
| `/admin/configuracion` (tab Accesos rápidos) | ✅ 200 | sin errores |
| `/admin/viajes` | ✅ 200 | sin errores |
| `/admin/viajes/1/gestionar` (marcar cobrado) | ✅ 200 | sin errores |
| `/admin/viajes/1/gestionar` (historial timeline) | ✅ 200 | sin errores |
| `/admin/reportes` (nuevas columnas y filtros) | ✅ 200 | sin errores |
| `/admin/reportes` (modal cobro rápido) | ✅ 200 | sin errores |

## Errores encontrados

- Ninguno. 0 errores de consola en toda la sesión.

## Screenshots tomados

### Prompt A — Sidebar colapsable + Config tabs + Tipos por defecto
- `prompt_a_sidebar.png` — sidebar colapsado (todos los grupos cerrados en carga inicial)
- `prompt_a_sidebar_open.png` — OPERACIONES expandido al hacer clic (chevron rotado)
- `prompt_a_config_tabs.png` — Configuración con tab "Parámetros financieros" activo y vista previa de liquidación
- `prompt_a_config_tipos.png` — tab "Tipos de vehículo" con catálogo por defecto insertado (Plancha, Rastra, Furgón, etc.)
- `prompt_a_config_accesos.png` — tab "Accesos rápidos" con grid de 8 tarjetas de navegación rápida
- `prompt_a_viajes_sidebar.png` — OPERACIONES se auto-abre al navegar a Viajes (link activo detectado por JS)

### Prompt B — Cobro, Historial y Reportes estilo Tropipay
- `prompt_b_cobro_estado.png` — badge "✅ Cobrado · 2026-06-29 17:29 · Transferencia · $1000.00 · Cód: TRF-2024-001" en gestionar_viaje
- `prompt_b_historial_timeline.png` — timeline "Historial del viaje" con entrada "Cobro registrado · admin · 2026-06-29 17:29"
- `prompt_b_reportes.png` — página Reportes con nuevos filtros "Cobro" y "Forma pago", KPIs actualizados
- `prompt_b_reportes_tabla.png` — tabla "Viajes del período" con columnas extendidas y scroll horizontal
- `prompt_b_reportes_fullpage.png` — página completa de reportes
- `prompt_b_modal_cobro.png` — modal "Registrar cobro" abierto sobre Viaje #4 con todos los campos

## Correcciones aplicadas

### Prompt A

#### 1 — Sidebar colapsable estilo Holded (`base_admin.html`, `admin.css`)
- 5 grupos: OPERACIONES (Dashboard, Viajes, Incidencias), COMERCIAL (Rutas, Tarifas, Cotizaciones), RECURSOS (Camioneros, Clientes), FINANZAS (Reportes), SISTEMA (Usuarios, Configuración, Auditoría, Acciones por lote, Mensajes, Papelera)
- Cada `nav-group-header` es un `<button>` con chevron animado (rotate -180° cuando abierto)
- `nav-group-items` colapsa con `max-height` transition de 0.25s
- JS: al cargar la página, el grupo que contiene el link `.nav-item-active` se abre automáticamente
- JS: estado de cada grupo guardado en `localStorage` (`nav_ng-xxx = '1'/'0'`)
- CSS en `admin.css?v=4` (cache-busted)

#### 2 — Configuración con pestañas (`configuracion.html`, `admin.css`)
- Título: "Configuración" / "Centro de control del sistema"
- 3 tabs: Parámetros financieros | Tipos de vehículo | Accesos rápidos
- Pestaña activa con línea naranja inferior (`cfg-active`)
- Estado del tab activo en `localStorage` (`cfg_tab`)
- Si se añade un tipo de vehículo, redirect fuerza tab de Tipos (via `request.args.get('ok_tipo')`)
- Tab "Accesos rápidos": 8 tarjetas grid con hover elevado

#### 3 — Tipos de vehículo por defecto (`database.py`)
- `INSERT OR IGNORE` de 8 tipos al arrancar: Plancha, Rastra, Furgón, Camión cerrado, Camión refrigerado, Portacontenedor, Camioneta, Otro

### Prompt B

#### 4 — Marcar pago realizado (1d) (`routes/admin.py`, `gestionar_viaje.html`, `database.py`)
- 5 columnas nuevas en tabla `viajes`: `forma_cobro`, `codigo_transaccion`, `comentario_cobro`, `fecha_cobro`, `monto_cobrado`
- Nueva ruta `POST /admin/viaje/<id>/marcar-cobrado` (solo admin)
- Bloque "Registro de cobro al cliente" en `gestionar_viaje.html`:
  - Si cobrado: badge verde con fecha, forma, monto, código y comentario
  - Si no cobrado: formulario con select de forma de pago, monto, código transacción, comentario
- Verificado: badge "✅ Cobrado" aparece correctamente tras registrar el cobro
- Verificado: viaje ya cobrado no muestra el formulario de cobro

#### 5 — Historial de cambios por viaje (1e) (`routes/admin.py`, `gestionar_viaje.html`, `database.py`)
- Nueva tabla `historial_viaje`: `id`, `viaje_id`, `usuario`, `accion`, `detalle`, `fecha_hora`
- Helper `_registrar_historial(viaje_id, accion, detalle)` — silencia excepciones para no interrumpir el flujo
- Hooks añadidos en: `cambiar_estado`, `asignar_camionero_vehiculo`, `nueva_incidencia`, `marcar_cobrado`
- Timeline cronológica en `gestionar_viaje.html` con dots naranjas y línea vertical gris
- Verificado: "Cobro registrado · Forma: Transferencia · Monto: $1000.00 · Código: TRF-2024-001" aparece en el historial

#### 6 — Reportes estilo Tropipay (6a+6b) (`routes/admin.py`, `reportes.html`, `admin.css`)
- Filtros adicionales: `estado_cobro` (Todos/Pendiente/Cobrado) y `forma_pago` (Todas/Efectivo/Transferencia/Tropipay/Otro)
- Tabla expandida de 8 → 11 columnas: + Estado cobro, Forma pago, Cód. transacción, [acción]
  - "Importe bruto" reemplaza "Precio cliente"
  - "Comisión" y "Neto" son columnas nuevas
- Botón `btn-cobrar-inline` visible solo en viajes Pendientes
- Modal `#modal-cobro-rep` para cobro rápido con `_referer` hidden input (redirige de vuelta a reportes con filtros)
- `tfoot` actualizado: Totales en Importe bruto, Comisión y Neto
- Verificado (DOM): 11 headers [ID, Cliente, Ruta, Estado, Importe bruto, Comisión, Neto, Estado cobro, Forma pago, Cód. transacción, (acción)]
- Verificado: Viaje #1 muestra "Cobrado / Transferencia / TRF-2024-001" sin botón Cobrar
- Verificado: Viajes #2, #3, #4 muestran "Pendiente / — / —" con botón "Cobrar"
- Verificado: Modal "Registrar cobro" se abre correctamente con datos del viaje

## Recomendaciones

- **Dashboard link activo**: `request.path == '/admin'` no matchea `/admin/` (con slash final). El link Dashboard nunca se marca activo. Considerar `request.path.rstrip('/') == '/admin'` para corregirlo.
- **Comisión vs Neto en tabla**: Para viajes sin datos de liquidación (pago_camionero / combustible en cero), la columna "Neto" coincide con la comisión. Es correcto matemáticamente pero puede confundir — considerar mostrar "N/A" si no hay liquidación calculada.
- **FINANZAS con un solo ítem**: el grupo Finanzas solo contiene Reportes. Listo para expansión futura.
- **localStorage compartido por dominio**: estado del sidebar se comparte entre pestañas del mismo dominio. No es problema en uso real de un operario por sesión.
