# Design tokens — Mercatoria Truck

Fuente de verdad de los design tokens del sitio. Esta carpeta es autocontenida:
un diseñador puede editar solo los `.json` de acá y regenerar el CSS sin tocar
lógica de la app ni templates.

## Qué hay en cada archivo

| Archivo | Contiene | Convención de nombres |
|---|---|---|
| `color.json` | 14 colores (fondo, panel, texto, semánticos peligro/exito/aviso/info, barra lateral) | **Español, plano** (`fondo`, `panel`, `texto`, `atenuado`, `peligro`...) — es la definición canónica. Ver "Renombrado a español" abajo. |
| `color-legacy.json` | Los 12 nombres viejos en inglés (`bg`, `text`, `muted`, `danger`...) que siguen en uso en `admin.css` y templates | Inglés, plano — cada clave es una **referencia** (`{fondo}`, `{texto}`...) al token español correspondiente en `color.json`, no un valor duplicado a mano. Ver por qué existe este archivo abajo. |
| `effects.json` | `shadow` y `radius` originales (intactos, en uso real vía `var(--shadow)`/`var(--radius)`) + escalas nuevas `radio-*` (4 pasos) y `sombra-*` (3 pasos) | Español + talla (`radio-sm/md/lg/pill`, `sombra-sm/md/lg`) |
| `typography.json` | Font-family por superficie, escala de tamaños, escala de pesos | Español + talla (`fuente-*`, `texto-*`, `peso-*`) |
| `spacing.json` | Escala de espaciado (padding/margin/gap) | Español + talla (`espacio-*`) |

Todos los valores son los que la app usa **hoy**, verificados con grep sobre
`templates/` y `static/css/admin.css` — no son valores de diseño nuevos ni
aspiracionales. El detalle completo del inventario (qué valor, cuántas veces
se usa, dónde) está en `plan_tokens.md` (raíz del repo, no comiteado — vive
localmente hasta que se apruebe borrarlo).

## Renombrado a español (color.json) — por qué existe `color-legacy.json`

`color.json` empezó en inglés porque se tomó tal cual del `:root` que ya
vivía en `admin.css`. Se renombró a español para que todo el vocabulario de
`tokens/` sea consistente en un solo idioma. Mapeo completo:

| Nombre viejo (inglés) | Nombre nuevo (español) | Valor |
|---|---|---|
| `bg` | `fondo` | `#f4f6fb` |
| `panel` | `panel` (sin cambio — ya es una palabra válida en español) | `#ffffff` |
| `panel-soft` | `panel-suave` | `#f8fafc` |
| `text` | `texto` | `#172033` |
| `muted` | `atenuado` | `#64748b` |
| `primary` | `principal` | `#155eef` |
| `primary-dark` | `principal-oscuro` | `#0f3ea8` |
| `border` | `borde` | `#e5e7eb` |
| `danger` | `peligro` | `#dc2626` |
| `success` | `exito` | `#16a34a` |
| `warning` | `aviso` | `#f59e0b` |
| `info` | `info` (sin cambio — funciona igual en ambos idiomas) | `#0891b2` |
| `sidebar` | `barra-lateral` | `#0f172a` |
| `sidebar-soft` | `barra-lateral-suave` | `#102a56` |

Es un renombrado puro — **ningún valor cambió**.

`admin.css` y 29 templates tienen **202 referencias `var(--nombre-viejo)`**
repartidas en 30 archivos (`admin.css` solo concentra 50; `gestionar_viaje.html`
otras 38). Reescribir esos 202 sitios para que digan `var(--peligro)` en vez
de `var(--danger)` fue evaluado y descartado por volumen/riesgo frente al
beneficio (cosmético, cero cambio visual) — en cambio, `color-legacy.json`
genera los 12 nombres viejos como **alias que resuelven al mismo valor** que
su equivalente español. `static/css/tokens.css` termina con ambos juegos de
variables (español, canónico + inglés, alias de compatibilidad), así que
ninguno de los 202 `var()` existentes se rompe.

**Consecuencia práctica:** un diseñador que solo edita `.json` ya trabaja
100% en español (ese era el objetivo). El código fuente de `admin.css` y los
templates sigue diciendo `var(--danger)` literalmente — migrar esos 202
sitios a los nombres nuevos es una tanda aparte, opcional, no parte de este
renombrado.

## Cómo regenerar `static/css/tokens.css`

```bash
npm install        # solo la primera vez, o si cambió package.json
npx style-dictionary build --config sd.config.json
# o, equivalente:
npm run tokens:build
```

Esto corre **en local**. Render no ejecuta Node — sigue sirviendo
`static/css/tokens.css` como archivo estático generado y comiteado. Después
de regenerar, revisar el diff (`git diff static/css/tokens.css`) antes de
commitear, para confirmar que solo cambió lo que se esperaba tocar.

**No editar `static/css/tokens.css` a mano.** Es el output del build — cualquier
edición manual se pierde en el próximo `style-dictionary build`.

**No tocar `admin.css` ni ningún template desde esta carpeta.** `tokens/`
solo define el catálogo de variables disponibles; que un archivo empiece a
usar `var(--espacio-md)` en vez de `12px` hardcodeado (o `var(--peligro)` en
vez de `var(--danger)`) es una tanda de aplicación aparte, con su propio plan
y verificación visual — no algo que se haga al mismo tiempo que se amplía o
renombra el catálogo.

## Vocabulario de nombres (compartido con Mercatoria Fuel)

Este vocabulario lo define Truck y lo hereda Fuel. La idea es que ambas apps
usen los mismos **nombres de escalón** aunque sus valores concretos no
coincidan exactamente — por eso ningún nombre lleva el valor literal
incrustado (nunca `--espacio-8`, siempre `--espacio-sm`). Así cada app puede
tener su propio número bajo el mismo nombre. Todo el vocabulario es español
desde esta tanda.

| Categoría | Prefijo | Escalones | Ejemplo |
|---|---|---|---|
| Color de fondo/panel/texto/borde | `fondo`, `panel`, `texto`, `atenuado`, `borde` | — (plano, sin escalón todavía) | `--fondo`, `--texto` |
| Color semántico | `peligro` / `exito` / `aviso` / `info` | — | `--peligro` |
| Familia tipográfica | `fuente-*` | `staff` / `cliente` / `landing` / `base` (superficie, no talla) | `--fuente-staff` |
| Tamaño de texto | `texto-*` | `xs` `sm` `md` `lg` `xl` `2xl` | `--texto-md` |
| Peso de fuente | `peso-*` | `regular` `semibold` `bold` `extrabold` | `--peso-bold` |
| Espaciado | `espacio-*` | `xs` `sm` `md` `lg` `xl` `2xl` | `--espacio-md` |
| Radio de borde | `radio-*` | `sm` `md` `lg` `pill` | `--radio-md` |
| Sombra | `sombra-*` | `sm` `md` `lg` | `--sombra-md` |

### Pendiente de diseño (documentado, no implementado): neutros por superficie

Truck hoy tiene un solo set de neutros (`--fondo`, `--texto`, `--atenuado`,
`--borde`) porque solo existía la superficie staff/admin cuando se creó
`color.json`. Fuel sí necesita valores de neutro **distintos** entre su
superficie de staff y su superficie de cliente. El patrón de nombres
acordado para cuando se haga esa tanda (en Truck o directamente en Fuel) es:

```
--{rol}-staff   /   --{rol}-cliente
```

sobre los nombres de rol que ya existen en `color.json` (ya en español) — por
ejemplo `--fondo-staff` / `--fondo-cliente`, `--texto-staff` /
`--texto-cliente`, `--atenuado-staff` / `--atenuado-cliente`, `--borde-staff`
/ `--borde-cliente`. No se implementa ahora: los 14 tokens de color de
`color.json` siguen planos y sin sufijo de superficie hasta que se apruebe
esa tanda explícitamente (implica fusionar/revisar valores casi-duplicados,
no es "cero cambio visual" garantizado como sí lo es este renombrado).

## Qué NO cubre esta ampliación

- No se migraron los 202 `var(--nombre-viejo)` existentes en `admin.css` y
  templates a los nombres nuevos en español — quedan resueltos vía
  `color-legacy.json` (ver arriba). Migrarlos es una tanda aparte, opcional.
- No se tokenizó la totalidad de los valores en uso (hay ~26 espaciados y
  ~40 tamaños de fuente distintos en el sitio hoy; solo se nombraron los
  dominantes de cada escala). Los valores fuera de la escala siguen
  hardcodeados hasta que se decida si entran o no en una escala futura.
- No se tokenizaron los anillos de foco de marca (`rgba(232,106,44,*)`) ni
  los overlays neutros menos frecuentes — son candidatos a su propio
  `sombra-focus` o mixin, pendiente de una pasada aparte.
- Ningún template ni `admin.css` consume todavía los tokens de tipografía,
  espaciado, radios o sombras agregados en la tanda anterior. Esa
  sustitución es la siguiente tanda posible, no parte de esta.
