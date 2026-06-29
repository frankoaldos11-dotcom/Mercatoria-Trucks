# Reporte de Pruebas — 2026-06-29

## Páginas probadas

| URL | HTTP | Consola |
|-----|------|---------|
| `/login` | ✅ 200 | sin errores |
| `/admin/clientes` | ✅ 200 | sin errores |
| `/admin/clientes/<id>/editar` | ✅ 200 | sin errores |
| `/admin/comercial/rutas` | ✅ 200 | sin errores |
| `/admin/comercial/rutas?access_error=...` | ✅ 200 | sin errores |
| `/admin/viajes` (con modal nuevo viaje) | ✅ 200 | sin errores |
| `/admin/camioneros` | ✅ 200 | sin errores |
| `/admin/configuracion` (sección tipos vehículo) | ✅ 200 | sin errores |

## Errores encontrados

- **favicon.ico 404** — pre-existente, no bloqueante

## Screenshots tomados

- `test_clientes_admin.png` — página clientes con formulario y campo documento_identidad
- `test_rutas_form.png` — formulario nueva ruta con campo tarifa/km auto
- `test_viajes_modal.png` — modal "Nueva solicitud de viaje" con selector de cliente
- `test_configuracion_tipos.png` — sección Tipos de vehículo en Configuración
- `test_ruta_duplicada_msg.png` — banner de error al intentar ruta duplicada

## Correcciones aplicadas

### 1a — Permisos operario: crear/editar/eliminar clientes
- Eliminados 3 checks `session.get("rol") != "admin"` en `routes/admin.py` (crear, editar, eliminar)
- Formulario "Nuevo cliente" visible para operario en `clientes.html`
- Columnas Email y Acciones (Editar/Eliminar) visibles para operario
- Excel import/export conservado solo para admin

### 1b — Permisos operario: crear/editar rutas
- Eliminados 2 checks de rol en `routes/comercial.py` (`nueva_ruta`, `editar_ruta`)
- Formulario "Nueva ruta" visible para operario en `rutas.html`

### 1c — Crear viajes desde admin
- Nuevo handler POST `/admin/viajes/nuevo` en `routes/admin.py`
- Botón "Nuevo viaje" en header de `/admin/viajes`
- Modal con formulario idéntico al portal cliente + selector de cliente
- Cierre con Escape y botón ✕
- El viaje se crea con estado `Pendiente` y se redirige a gestionar viaje

### 2 — Tipos de vehículo integrado en camioneros
- Link "Tipos de vehículo" eliminado del sidebar (`base_admin.html`)
- Selector "Tipo de vehículo" en formulario nuevo camionero usa `tipos_vehiculo` (antes `catalogo_tipo_transporte`)
- Selector actualizado también en formulario editar camionero
- Sección de gestión de tipos_vehiculo añadida a `/admin/configuracion` (CRUD: add/delete)
- Nuevas rutas en `finanzas.py`: `/admin/configuracion/tipo-vehiculo/nuevo` y `/eliminar`

### 3 — Tarifas automáticas en nueva ruta
- Campo `tarifa_km` añadido al formulario "Nueva ruta"
- JS: al cambiar km, calcula `tarifa_sugerida = km × tarifa_km_global` y pre-rellena el campo
- El usuario puede sobreescribir el valor sugerido
- `tarifa_km_global` se pasa desde `routes/comercial.py` via `get_configuracion()`

### 4 — Clientes sin duplicados: campo documento_identidad
- Migración `ADD COLUMN documento_identidad TEXT` en `database.py`
- Validación de email duplicado al crear cliente (redirige con `access_error`)
- Validación de documento_identidad duplicado al crear cliente
- Mismas validaciones en editar cliente (excluye el propio id)
- Campo visible en formulario de nuevo cliente y edición

### 7 — Autocomplete origen/destino en rutas
- `<datalist id="dl-origenes-destinos">` en `rutas.html` con todos los orígenes/destinos existentes
- Inputs de Origen y Destino en nueva ruta tienen `list="dl-origenes-destinos"`
- Datos se pasan desde `routes/comercial.py` sin petición extra al servidor

### 8 — Mensaje ruta duplicada
- Verificado: banner rojo visible en la parte superior de la página con texto claro
- Mensaje: "Esta ruta ya existe. Si necesitas modificarla, búscala en el listado y edítala."
- Implementación ya existente de la sesión anterior — confirmada funcional ✅

## Recomendaciones

- **Poblar tipos_vehiculo iniciales**: el catálogo está vacío en nuevas instancias. Considerar añadir valores por defecto en `database.py` (Plancha, Rastra, Furgón, Portacontenedor, etc.) igual que se hace con `catalogo_tipo_transporte`
- **Autocomplete en modal nuevo viaje**: el formulario modal usa `<select>` para la ruta (bien), pero los campos de observaciones son texto libre — no requiere autocompletar
- **Email como campo recomendado**: se eliminó el `required` del campo email en nuevo cliente para que operarios puedan registrar clientes sin email; revisar si se desea mantener validación de formato cuando se provee
