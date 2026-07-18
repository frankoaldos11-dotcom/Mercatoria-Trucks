# Reporte de Pruebas — 2026-07-18 (Tres arreglos en el detalle de viaje)

## Contexto
Tres reportes de producción sobre `/admin/viaje/<id>`: botón "Confirmar" de combustible sin efecto, imposibilidad de descargar la Orden de Carga desde el paso 2, y rutas sin zona que dejan el combustible en $0.00 sin forma clara de resolverlo.

## Páginas probadas (local, `127.0.0.1:5001` — el 5000 está ocupado por un proceso ajeno que Aldo diagnostica aparte)
- `/login`, `/admin/viaje/<id>`, `/admin/comercial/rutas`

## Investigación previa a la implementación (BUG 1)
Se probó el envío real del formulario de combustible de varias formas (clic disparado por JS, clic real vía automatización, litros válidos/vacíos, sesión fresca/vieja) antes de tocar código. No se reprodujo "cero peticiones, cero errores" como se describió originalmente; se encontraron dos grietas reales en su lugar (campo litros sin `required`, y error CSRF mostrando una página cruda de Werkzeug en vez de un mensaje de la app). Confirmado con Aldo, se aplicaron esas dos mejoras.

## Pruebas realizadas
1. **BUG 1**: clic real (`btn.click()`) en "Confirmar" con litros válidos y sesión fresca → combustible confirmado correctamente ("Combustible confirmado · 510.0 L · $1326.00"). Con litros vacíos → `form.checkValidity()` devuelve `false`, el navegador bloquea el envío, no llega al servidor. Con un `csrf_token` deliberadamente inválido → ya no cae en la página cruda "400 Bad Request" de Werkzeug; redirige a la misma página del viaje con el banner rojo de error ya existente ("Tu sesión en esta página venció. Intenta de nuevo.").
2. **BUG 2**: en un viaje con transportista y vehículo asignados, el paso 2 muestra "Ver Orden de Carga" y "Ver Carta de Porte" — ambos descargan (`GET /admin/viaje/<id>/pdf` y `/carta-porte`, status 200, `content-type: application/pdf`). En un viaje sin vehículo asignado, el paso 2 muestra un botón deshabilitado con `title="Falta: vehículo"` en vez de no mostrar nada.
3. **BUG 3**: en el formulario "Nueva ruta", el `<select name="zona">` ahora lista únicamente lo que hay en `zonas_combustible` (Occidente, Oriente — sin la opción "Centro" que no existe en esa tabla), es `required`, y el formulario resulta inválido si no se elige zona. En el modal "Editar ruta", abierto sobre la ruta real La Habana→Holguín (la que tiene zona vacía en la base), el select no queda preseleccionado en ninguna opción real y el formulario también resulta inválido hasta elegir una zona — confirma que la ruta rota queda visiblemente señalada para que Aldo la resuelva desde ahí.
4. `python -m py_compile` sobre los `.py` tocados — sin errores. Templates parseados vía `app.jinja_env.get_template()` — sin errores.

## Errores encontrados
Ninguno funcional en el código nuevo. Ver la nota de BUG 1 arriba: la investigación no reprodujo el síntoma exacto reportado originalmente, y esto se documentó y confirmó con Aldo antes de implementar, en vez de adivinar una causa raíz falsa.

## Screenshots tomados
Ninguno — verificación hecha vía inspección de DOM/`fetch`/`checkValidity()` por las limitaciones de clic-por-coordenada de la herramienta de automatización en este entorno (documentadas y sorteadas con clics disparados por JS sobre los elementos reales, no simulacros).

## Correcciones aplicadas
`app.py` (`required` no aplica aquí — ver login: se agregó lectura de `error` en `GET /login` + `@app.errorhandler(CSRFError)`), `templates/admin/gestionar_viaje.html` (`required` en input de litros; paso 2 con rama `{% else %}` deshabilitada + tooltip, y enlace nuevo a Carta de Porte), `routes/comercial.py` (`rutas()` pasa `zonas_combustible`; `nueva_ruta()`/`editar_ruta()` validan zona no vacía; `editar_ruta()` migrado de placeholders `?` a `ph()`), `templates/admin/comercial/rutas.html` (selects de zona dinámicos y obligatorios en creación y edición).

## Datos de prueba y limpieza
- Viaje #2: se confirmó combustible durante la verificación (510.0 L / $1326.00) — revertido a `NULL`/`NULL` al finalizar.
- Viaje #1: solo se probaron envíos que el navegador bloqueó (litros vacío) o que el backend rechazó (CSRF inválido) — sin mutación en ningún momento.
- No se creó ninguna ruta de prueba (el formulario se completó para probar `checkValidity()`, nunca se envió).
- Servidor Flask (puerto 5001) detenido tras confirmación explícita. `Get-Process python` solo muestra el proceso ajeno del puerto 5000, sin tocar.

## Recomendaciones
- La ruta `La Habana → Holguín` sigue sin zona en la base — quedó señalada visualmente en el modal de edición para que Aldo la complete él mismo (no se completó por código, ver plan aprobado).
- No se agregó restricción a nivel de base de datos (`NOT NULL`/`CHECK`) sobre `rutas.zona` — decisión documentada en el plan, disponible si se prefiere reforzarlo también ahí.
