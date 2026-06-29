# Reporte de Pruebas — 2026-06-28

## Páginas probadas

| URL | HTTP | Consola |
|-----|------|---------|
| `/login` | ✅ 200 | sin errores nuevos |
| `/admin/` (dashboard) | ✅ 200 | sin errores |
| `/admin/viaje/1` (flujo rediseñado) | ✅ 200 | sin errores |
| `/admin/configuracion` (bug fix) | ✅ 200 | sin errores |
| `/admin/incidencias` | ✅ 200 | sin errores |

## Errores encontrados

- **favicon.ico 404** — sin favicon registrado en Flask (pre-existente, no bloqueante)
- **500 en `/admin/camioneros/1/editar`** — error de sesión anterior, no reproducido en esta sesión

## Screenshots tomados

- `test_viaje_steps.png` — flujo de viaje rediseñado con pasos 1-7
- `test_configuracion_fix.png` — formulario configuración sin spinners

## Correcciones aplicadas

### 1. Flujo de viaje rediseñado (`templates/admin/gestionar_viaje.html`)
- **Eliminado** el paso 1 "Prioridad" de la lista de pasos secuenciales
- **Movida** la edición de Prioridad al panel de información superior como control inline (radio buttons compactos)
- **Añadido** "Km liquidables" al panel de info superior
- **Renumerados** los pasos: Asignar camionero = 1, Confirmar precio = 2, Combustible = 3, Fecha extracción = 4, Fecha descarga = 5, Enviar documentación = 6, Confirmar entrega = 7, Cerrar operación = 8
- Pasos completados aparecen colapsados en verde; pasos pendientes aparecen como tarjetas activas

### 2. Campos numéricos sin flechitas
- `templates/cliente/solicitar.html`: `cantidad_contenedores` ya era `type="text"` con `inputmode="numeric"` ✅
- `templates/admin/configuracion.html`: CSS `.config-input` ya tenía `-moz-appearance: textfield` y webkit spin-button supresión ✅

### 3. Bug configuración no guarda (`services/finanzas_service.py`)
- **Root cause**: parámetros invertidos en `guardar_configuracion()` — se pasaba `(float(valor), clave)` en lugar de `(clave, float(valor))` tanto para SQLite como PostgreSQL. La columna `clave` recibía el valor numérico y la columna `valor` recibía el nombre de la clave, por lo que `ON CONFLICT(clave)` nunca encontraba match y se insertaban filas con datos erróneos.
- **Fix**: invertido a `(clave, float(valor))` en ambas ramas.
- **Verificado**: se guardó `tarifa_km = 2.25`, se recargó la página, el valor persiste ✅

### 4. Mensaje km mínimo (`templates/admin/gestionar_viaje.html`)
- Simplificado: eliminado el "( X km reales)" del final del aviso
- Nuevo texto: "Se aplica el mínimo de X km para esta liquidación porque la ruta tiene menos km registrados."
- Visible para admin y operario (no gateado por rol)

### 5. Logo móvil (`templates/admin/base_admin.html`)
- Bumpeada versión CSS: `?v=2` → `?v=3` para forzar recarga de caché
- Añadido `min-width:24px` y `aria-hidden="true"` al SVG del topbar móvil para asegurar renderizado

### 6. Incidencias en sidebar
- Enlace `/admin/incidencias` ya existía en el sidebar bajo SISTEMA ✅
- Ruta devuelve HTTP 200 ✅

### 7. Cartel informativo en dashboard admin
- Bloque de información ya existía en `/admin/` ✅

## Recomendaciones

- **`/admin/camioneros/1/editar` — 500**: Investigar si el error persiste en una sesión limpia; puede ser un dato huérfano en la DB de pruebas
- **favicon.ico**: Registrar la ruta `/favicon.ico` en Flask o confirmar que el archivo existe en `/static/favicon.ico`
- Restaurar el valor `tarifa_km` a `1.5` si se usó solo para prueba (actualmente está en `2.25`)
