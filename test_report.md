# Reporte de Pruebas — 2026-07-17 (Exportar/Importar Rutas)

## Contexto
Rutas ya tenía botones de Exportar/Importar apuntando al mecanismo genérico compartido con camioneros/vehículos (columnas incompletas, dedup por `id`, sin validación ni resumen). Se reemplazó el backend detrás de esos botones por uno dedicado a rutas: export con las 6 columnas reales (origen, destino, km oficiales, tarifa por km, zona, activa), import con dedup por origen+destino (nunca pisa), validación de filas, aviso de zona no reconocida sin inventarla, y resumen detallado en la UI.

## Páginas probadas (local, `127.0.0.1:5001` — ver nota de puerto abajo)
- `/login`, `/admin/comercial/rutas`
- `/admin/exportar/rutas`, `POST /admin/comercial/rutas/importar`

## Pruebas realizadas
1. Export vía UI: descargado y verificado con `openpyxl` — columnas exactas `ORIGEN, DESTINO, KM_OFICIALES, TARIFA_KM, ZONA, ACTIVA`, datos correctos, `activa` formateado "Sí"/"No".
2. Import con un Excel de 4 filas: una ruta nueva con zona válida (creada), una duplicada por origen+destino exacto de una existente (omitida, ruta original sin modificar — confirmado en BD), una con km no numérico (omitida, no llegó a insertarse), una con zona inexistente en `zonas_combustible` (creada igual, con aviso explícito en el resumen y confirmado que `zonas_combustible` no ganó ninguna fila nueva). Auditoría registrada: "Importó rutas desde Excel: 2 creadas, 1 duplicadas, 1 inválidas".
3. Resumen en la UI (banner tras redirect) lista correctamente creadas/duplicadas/inválidas por "origen → destino" y el motivo de cada inválida, más el aviso aparte de zona no reconocida.
4. Acceso operador: cuenta de prueba con rol `operador` — no ve ninguno de los dos botones en la plantilla; `GET /admin/exportar/rutas` redirige a `/admin/`; `POST /admin/comercial/rutas/importar` (con CSRF válido) redirige con `access_error=Sin+permisos+para+importar+rutas`.
5. `python -m py_compile` sobre los 2 `.py` tocados — sin errores. Template parseado vía `app.jinja_env.get_template()` — sin errores.

## Errores encontrados
- Ninguno funcional en el código nuevo. Incidente de entorno: el puerto 5000 de esta máquina está ocupado por un proceso ajeno no identificado (que Aldo confirmó viene arrastrando hace varias sesiones y va a diagnosticar él mismo por separado) — la verificación de esta tanda se corrió contra el puerto 5001 en su lugar, lanzando la app con un launcher que evita el bloque `if __name__ == "__main__"` (hardcodea el 5000) sin tocar `app.py`.
- El Chrome MCP no permite adjuntar archivos locales directamente a un `<input type="file">` (restricción de la herramienta, no del código); el import se verificó end-to-end vía POST autenticado (cookies + CSRF reales) desde un script Python, ejercitando el endpoint real igual que lo haría un navegador.

## Screenshots tomados
- Login y `/admin/comercial/rutas` mostrando el nuevo texto de columnas esperadas y las rutas existentes.

## Correcciones aplicadas
`routes/admin.py` (`_EXCEL_CONFIG["rutas"]["columnas"]` corregido + formateo Sí/No para columnas `activa`/`activo` en `exportar_excel`), `routes/comercial.py` (nuevo endpoint `importar_rutas_excel`, `rutas()` ahora pasa `resumen_import` desde `session`), `templates/admin/comercial/rutas.html` (form de importar apunta al nuevo endpoint, texto de columnas esperadas, banner de resumen detallado).

## Datos de prueba y limpieza
- Cuenta `_test_operador_rutas` (rol operador): creada y eliminada.
- Rutas de prueba (Cienfuegos→Trinidad, Pinar del Rio→Vinales, Guantanamo→Baracoa): creadas durante la verificación del import y eliminadas al finalizar. Las 3 rutas originales (La Habana→Santiago/Holguin/Matanzas) quedaron intactas, sin pisar.
- Servidor Flask (puerto 5001) detenido correctamente tras confirmación explícita del usuario. `Get-Process python` confirma que no queda proceso propio vivo (el PID ajeno del puerto 5000, fuera del alcance de esta sesión, no se tocó).

## Recomendaciones
- El endpoint genérico `/admin/importar/rutas` (el viejo, por `id`) queda sin ningún botón que lo apunte pero no se eliminó ni se bloqueó explícitamente — decisión documentada en el plan aprobado, pendiente de confirmación de Aldo si prefiere que se bloquee.
