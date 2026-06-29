# Reporte de Pruebas — 2026-06-28

## Páginas probadas (viewport móvil 390×844)
- http://127.0.0.1:5000/admin/ — dashboard (sidebar cerrado)
- http://127.0.0.1:5000/admin/ — dashboard (menú overlay abierto con hamburguesa)
- http://127.0.0.1:5000/admin/viaje/2 — gestionar viaje (flujo secuencial en móvil)

## Errores encontrados
Ninguno. Sin errores de consola ni HTTP 4xx/5xx.

## Screenshots tomados
- `mobile_dashboard_closed.png` — topbar fija visible, sidebar oculto, contenido principal accesible
- `mobile_menu_open.png` — menú overlay a pantalla completa con links verticales
- `mobile_viaje_detail.png` — página de viaje con pasos secuenciales en móvil (fullPage)

## Correcciones aplicadas

### CSS admin.css — bloque @media (max-width: 768px) reescrito completamente

Comportamiento anterior (roto):
- `.sidebar` usaba `position: fixed; left: -290px` con `transition: left` — el drawer se animaba pero en algunos dispositivos quedaba parcialmente visible bloqueando el contenido
- `.main-content` tenía `padding: 14px` sin offset del topbar — el contenido quedaba tapado por la barra superior
- `.mobile-topbar` era `position: sticky` — no quedaba fija al hacer scroll

Comportamiento nuevo:
1. **Sidebar completamente oculto** por defecto: `display: none`
2. **Topbar fija**: `position: fixed; top: 0; left: 0; right: 0; z-index: 600` — siempre visible sobre todo el contenido
3. **Menú overlay a pantalla completa**: al pulsar ☰, el sidebar pasa a `display: flex; position: fixed; top: 52px; width: 100vw; height: calc(100vh - 52px); z-index: 500`
4. **Overlay oscuro**: `top: 52px` — cubre la zona de contenido sin tapar la topbar
5. **Contenido principal**: `padding: 66px 14px 32px` — desplazado 66px desde arriba para quedar bajo la topbar de 52px
6. **html/body**: `height: auto; overflow-y: auto` — sin alturas fijas

### Template — cache-buster en CSS
`base_admin.html`: `admin.css?v=2` para forzar recarga de la hoja de estilos tras el cambio.

## Comportamiento verificado
| Check | Resultado |
|-------|-----------|
| `.sidebar` display en reposo | `none` ✓ |
| `.sidebar` width al abrir | `390px` (100vw) ✓ |
| `.sidebar` top al abrir | `52px` (bajo topbar) ✓ |
| `.main-content` padding-top | `66px` ✓ |
| `.mobile-topbar` position | `fixed` ✓ |
| `.mobile-topbar` z-index | `600` ✓ |
| Cerrar menú con botón X | Funciona ✓ |

## Recomendaciones
- El botón X cierra el menú correctamente; el overlay oscuro es visual pero no clickeable (el sidebar cubre todo el ancho). Si se prefiere cerrar tocando fuera del menú, reducir el sidebar a ~85% del ancho para dejar una franja clickeable.
- Incrementar `?v=3` en la próxima modificación de admin.css para invalidar caché.
