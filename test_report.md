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

## Errores encontrados

- Ninguno. 0 errores de consola en toda la sesión.

## Screenshots tomados

- `prompt_a_sidebar.png` — sidebar colapsado (todos los grupos cerrados en carga inicial)
- `prompt_a_sidebar_open.png` — OPERACIONES expandido al hacer clic (chevron rotado)
- `prompt_a_config_tabs.png` — Configuración con tab "Parámetros financieros" activo y vista previa de liquidación
- `prompt_a_config_tipos.png` — tab "Tipos de vehículo" con catálogo por defecto insertado (Plancha, Rastra, Furgón, etc.)
- `prompt_a_config_accesos.png` — tab "Accesos rápidos" con grid de 8 tarjetas de navegación rápida
- `prompt_a_viajes_sidebar.png` — OPERACIONES se auto-abre al navegar a Viajes (link activo detectado por JS)

## Correcciones aplicadas

### 1 — Sidebar colapsable estilo Holded (`base_admin.html`, `admin.css`)
- 5 grupos: OPERACIONES (Dashboard, Viajes, Incidencias), COMERCIAL (Rutas, Tarifas, Cotizaciones), RECURSOS (Camioneros, Clientes), FINANZAS (Reportes), SISTEMA (Usuarios, Configuración, Auditoría, Acciones por lote, Mensajes, Papelera)
- Incidencias movida de "flotante" a dentro de OPERACIONES
- Cotizaciones movida a dentro de COMERCIAL (antes aparecía sola en OPERACIONES)
- Badge "Solo Admin" eliminado del sidebar (los items admin-only están en grupos que Jinja2 oculta para operario)
- Cada `nav-group-header` es un `<button>` con chevron animado
- `nav-group-items` colapsa con `max-height` transition de 0.25s
- JS: al cargar la página, el grupo que contiene el link `.nav-item-active` se abre automáticamente
- JS: estado de cada grupo guardado en `localStorage` (`nav_ng-xxx = '1'/'0'`)
- Mobile hamburguesa sin cambios (sigue funcionando con `.mobile-open`)
- CSS en `admin.css?v=4` (cache-busted)

### 2 — Configuración con pestañas (`configuracion.html`, `admin.css`)
- Título cambiado a "Configuración" / "Centro de control del sistema"
- 3 tabs: Parámetros financieros | Tipos de vehículo | Accesos rápidos
- Pestaña activa con línea naranja inferior (`cfg-active`)
- Estado del tab activo en `localStorage` (`cfg_tab`)
- Si se añade un tipo de vehículo, el redirect fuerza el tab de Tipos (via `{% if request.args.get('ok_tipo') %}`)
- Tab "Accesos rápidos": 8 tarjetas grid con hover elevado — Usuarios, Rutas, Tarifas, Auditoría, Camioneros, Clientes, Reportes, Acciones por lote
- Vista previa de liquidación sigue reactiva en tab Parámetros

### 3 — Tipos de vehículo por defecto (`database.py`)
- Tras `CREATE TABLE IF NOT EXISTS tipos_vehiculo`, se insertan 8 valores con `INSERT OR IGNORE`:
  Plancha, Rastra, Furgón, Camión cerrado, Camión refrigerado, Portacontenedor, Camioneta, Otro
- Confirmado en tab Tipos de vehículo: todos aparecen en el catálogo desde primer arranque

## Recomendaciones

- **Dashboard link activo**: `request.path == '/admin'` no matchea `/admin/` (con slash final). El link Dashboard nunca se marca activo. Considerar `request.path.rstrip('/') == '/admin'` para corregirlo.
- **FINANZAS con un solo ítem**: el grupo Finanzas solo contiene Reportes. Si en el futuro se añaden más reportes o un módulo de facturación, el grupo ya está listo para expandirse.
- **localStorage compartido por dominio**: si se abre la app en dos pestañas con distintos roles, el estado del sidebar se comparte. No es un problema en uso real (un operario por sesión), pero es un detalle a considerar.
