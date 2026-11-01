# Registro de decisiones de diseño

Práctico Integrador 2026 — Fase previa común: Ingeniería de datos y automatización (MDM / ETL).

Cada decisión registra: **contexto** (qué problema apareció en los datos o en la consigna),
**opciones evaluadas**, **decisión** y **criterio** (la evidencia y el razonamiento que la respaldan).
Todas fueron discutidas y aprobadas por el equipo el 01/11/2026, a partir del diagnóstico de datos
(ver [diagnostico_datos.md](diagnostico_datos.md)).

---

## D1 — La base maestra lleva los 2.184 artículos

**Contexto.** La consigna pide un *Inner Join* `ERP[CodigoProveedor] = Proveedor[Cod.Articulo]`
(que dejaría solo los cruzados) pero el Entregable 1 exige *"los 2.184 registros consolidados"*.
El cruce da 2.042 artículos cruzados y 142 que no cruzan.

**Opciones.** (a) 2.184 filas, con los datos de Fispa vacíos donde no hubo cruce; (b) solo las 2.042
cruzadas; (c) 2.184 filas más una columna extra `Estado_Cruce`.

**Decisión.** (a) 2.184 filas. Los 142 no cruzados quedan con Costo_Reposicion, EAN13, Cruces_OEM,
Aplicacion_Completa y URL_Foto vacíos, y además figuran en `errores_sin_mapeo.csv` con su motivo.

**Criterio.**
- El Entregable 1 y el "Filtro Estricto de Demanda" hablan de los **SKU activos de la empresa**: el
  universo de la base lo define el ERP, no el proveedor.
- El *Inner Join* se interpreta como regla de **enriquecimiento**: un artículo solo recibe datos de
  Fispa si hay correspondencia unívoca. Lo que el Inner Join excluye son los artículos del proveedor
  que la empresa no vende (3.668 − 2.042 = 1.626 artículos), y eso se cumple.
- Sacar 142 SKU activos de la base que alimenta e-commerce y facturación los volvería invisibles
  para la venta. El log de excepciones ya los identifica para corregirlos.
- No se agrega columna extra para respetar exactamente el esquema del Anexo 2. El estado de cada
  artículo surge del log.

## D2 — EAN13 vacío y documentado

**Contexto.** El Anexo 2 pide `EAN13` desde `CodigoBarras`. En la lista, **ningún** valor es un
EAN-13 (13 dígitos numéricos): 3.656 de 3.668 son iguales a `Cod.Articulo` y algunos traen
caracteres basura (`_x001F_30298`). La web de Fispa tampoco publica códigos de barras.

**Opciones.** (a) Dejarlo vacío y documentarlo; (b) copiar el valor crudo; (c) buscarlo en la web.

**Decisión.** (a) Vacío. El pipeline valida cada valor (13 dígitos más dígito verificador GS1) y solo
carga los válidos.

**Criterio.** Un campo llamado EAN13 que contiene un código interno es un **dato falso**. Los canales
digitales (marketplaces, lectores de código de barras) lo tomarían como un GTIN real. Un dato
ausente se detecta, uno falso contamina. La opción (c) no es viable porque la web no publica códigos
de barras. Si una lista futura trae EAN válidos, se cargan solos, sin tocar el código.

**Por qué no se elimina la columna.** EAN13 forma parte del esquema obligatorio del Anexo 2
(columna 8): eliminarla haría que la base no cumpla el Entregable 1. Se mantiene vacía y con la
validación activa, para que se complete sola cuando el proveedor entregue códigos válidos.

## D3 — Descripcion_Optimizada generada por reglas

**Contexto.** Hay que generar 2.184 descripciones de una línea, de 70 a 90 caracteres
aproximadamente, con la forma [Tipo de pieza] + [Aplicación principal], sin repetir "FISPA".

**Opciones.** (a) Reglas deterministas; (b) LLM (API); (c) reglas con LLM opcional.

**Decisión.** (a) Reglas:
1. **Tipo de pieza** = `Descripcion` del proveedor sin el código de artículo ni aclaraciones entre
   paréntesis (`"BOBINA DE IGNICION 70275"` → `"BOBINA DE IGNICION"`). Es el nombre oficial y
   sin abreviaturas.
2. **Aplicación** = nombre del ERP sin las palabras iniciales que describen el tipo. Para detectarlas
   se compara con el tipo y la categoría, tolerando plurales y abreviaturas
   (`"BULBO TEMP.AUDI A3"` → `"AUDI A3"`).
3. Si el resultado queda **por debajo de 70** caracteres y la `Aplicacion` del proveedor es más
   completa, se usa esa. Se normalizan cilindradas (`"1 6"` → `"1.6"`).
4. Se elimina "FISPA", se recorta en palabra completa a **90 como máximo** y se limpian
   separadores colgantes.
5. Para los artículos no cruzados se usa el nombre del ERP, que ya tiene la forma tipo + aplicación,
   recortado.
6. Se quitan las palabras con **forma de código OEM**, es decir, 6 o más dígitos seguidos
   (`"RALENTI ASTRA-VECTRA-ZAFIRA GM90411546"` → `"RALENTI ASTRA-VECTRA-ZAFIRA"`). También se
   quita la palabra que anuncia el código (`OEM`, `ORIG.`). Esos códigos ya están en Cruces_OEM.
7. Todo el texto se pasa a **mayúsculas**: 716 descripciones mezclaban mayúsculas y minúsculas
   (`"FORD Courier 1.8 D Endura"`).
8. Las **cilindradas** se escriben con punto también cuando el texto viene del nombre del ERP
   (`"STILO 1 8 16V"` → `"STILO 1.8 16V"`). Antes la regla 3 solo se aplicaba al texto de
   Fispa, y la columna mezclaba los dos formatos. No se tocan números que ya tienen punto o
   coma (`"2 1.5"` y `"1,6 8V"` quedan igual).
9. Las **abreviaturas pegadas** a la palabra siguiente se separan con un espacio
   (`"JGO JUNTAS INYECT.RENAULT"` → `"JGO JUNTAS INYECT. RENAULT"`). La abreviatura no se
   expande: decidir si `INYECT.` es "inyección" o "inyector" sería interpretar.

**Criterio.** Es **determinista y reproducible** (misma entrada, misma salida), **gratis**, no
requiere API key (el administrativo ejecuta todo con doble clic) y cada resultado se puede explicar
regla por regla en la defensa. La regla 3 aprovecha los caracteres disponibles con datos reales
(más modelos y motores), lo que mejora la búsqueda. No se rellena con texto artificial.

Sobre las reglas 6 a 9 (agregadas tras revisar el contenido de la base). Las reglas 8 y 9
corrigieron 38 y 67 descripciones respectivamente:
- El umbral de 6 dígitos seguidos separa los códigos de los datos de aplicación. Años
  (`2003/2008`), cilindradas (`1.6`) y códigos de motor (`K4M700`) nunca llegan a 6 dígitos
  seguidos.
- Las palabras se analizan separando por `-` y `/`, así no se pierden modelos pegados a un
  código.
- Códigos con menos de 6 dígitos seguidos (`BAE4DS9275C`, `78410SV4003`) quedan, porque
  bajar el umbral empezaría a borrar datos reales.
- Los errores de tipeo del ERP (`TOYOYA`, `CHEVROLER`) no se corrigen: hacerlo sería adivinar.

**Resultado.**
- 0 descripciones superan los 90 caracteres, 0 contienen "FISPA", 0 tienen códigos de 6 o más
  dígitos y 0 tienen minúsculas.
- 1.320 quedan entre 70 y 90 caracteres.
- El resto es más corto porque el origen no tiene más información útil (ej.
  `"INYECTOR CORSA 1.0 8V"`).
- Al quitar los códigos (183 descripciones afectadas), las de menos de 40 caracteres pasaron de
  92 a 126: era espacio ocupado por códigos, no por información para buscar.

**Control de descripciones repetidas** (mismo texto en distinto Codigo_Interno):

| Momento | Descripciones repetidas | Artículos involucrados |
|---|---|---|
| Antes de las reglas 6 a 9 | 25 | 51 |
| Después de las reglas 6 y 7 | 24 | 49 |
| Después de las reglas 8 y 9 (final) | 26 | 53 |

- Quitar los códigos OEM **no generó ninguna repetida nueva**.
- Los grupos que aparecieron ya eran el mismo texto escrito distinto. Al estandarizar quedó a la
  vista que eran iguales, sin que se perdiera información:
  - `11040 FISPA` y `11041 FISPA` solo se distinguían por un carácter roto (en uno "O RINGS" con
    espacio, en el otro con un acento grave en lugar del apóstrofo; D11);
  - `81043`/`84027` y `81413`/`84020` solo se distinguían por escribir la cilindrada "2 3" o
    "2.3" (regla 8).
- El resto ya venía repetido del origen: sus nombres en el ERP son prácticamente iguales (ej. 3 ×
  "BULBO DE TEMPERATURA DE ELECTROVENTILADOR CHEVROLET TODOS").
- No se desambiguan agregando texto, porque sería inventar diferencias que el origen no tiene.
  Se distinguen por Codigo_Interno y Codigo_Proveedor, que están en la misma fila.

## D4 — Clave de cruce: solo trim + mayúsculas

**Contexto.** La consigna exige cruce determinista, sin estimaciones ni *fuzzy matching*. Los códigos
tienen formatos variados (`MAF007`, `FI-0280155919`, `FIS-001`).

**Opciones.** (a) Exacto puro; (b) trim + mayúsculas; (c) además quitar espacios y guiones internos.

**Decisión.** (b) Se quitan los espacios de los extremos y se pasa a mayúsculas. Antes de cruzar se
verifica que la clave normalizada sea única en la lista del proveedor. Si no lo es, el proceso se
detiene con error.

**Criterio.** Medido sobre los datos, las tres opciones dan **exactamente 2.042** cruces y ninguna
genera colisiones. Las diferencias de formato que se veían ("MAF 032" vs "MAF032") son entre el
código interno y el de proveedor, no entre el ERP y la lista. La opción (b) protege contra
exportaciones futuras con espacios o minúsculas sin dejar de ser igualdad 1 a 1. La opción (c)
podría igualar códigos que el fabricante considera distintos (`FI-028` ≠ `FI 028`).

## D5 — Columnas duplicadas de la lista: se usan las del Anexo 2

**Contexto.** La lista trae `Cod.Ref.Aux` y `Referencia`, `Aplicacion` y `Cod.Linea`, y dos
columnas `Linea.Descripcion`.

**Decisión.** Se usan `Cod.Ref.Aux` (→ Cruces_OEM) y `Aplicacion` (→ Aplicacion_Completa), que son
las que nombra el Anexo 2.

**Criterio.** Se verificó fila por fila que las copias son **idénticas en las 3.668 filas**. El
pipeline repite esa verificación en cada corrida y avisa en el log si alguna vez difieren.

## D6 — Códigos de proveedor compartidos por dos SKU

**Contexto.** `120103 FISPA` y `120107 FISPA` tienen el mismo Codigo Proveedor `120107`. Lo mismo
pasa con `M1015 FISPA` y `M1023 FISPA`, que comparten `M1015`.

**Decisión.** Se enriquecen ambos SKU con el mismo artículo de Fispa. Se registra un aviso en
`log_proceso.txt` y no se cuentan como excepción.

**Criterio.** Cada SKU sigue teniendo **una sola** correspondencia en la lista, así que el cruce
sigue siendo unívoco desde el ERP. El ERP no se puede modificar (inmutabilidad), así que el
pipeline no "elige" uno: deja el caso trazado para que Compras lo revise.

## D7 — Columna Sugerencia_Revision en el log de excepciones

**Contexto.** Algunos códigos no cruzados tienen un código casi igual en la lista
(ej. `285600` → existe `285600A`).

**Decisión.** `errores_sin_mapeo.csv` incluye la columna informativa `Sugerencia_Revision`
("Posible equivalente en lista: X (verificar manualmente)"). Esa sugerencia **nunca** se usa para
cruzar.

**Criterio.** Ayuda a la persona que corrige el ERP sin violar la regla de "sin estimaciones": la
máquina sugiere y el humano decide. Criterios de sugerencia: igualdad ignorando espacios y guiones,
o diferencia de una letra final. En esta corrida hay 9 sugerencias.

## D8 — URL_Foto: imagen publicada en `productos/c/`

**Contexto.** El sitio publica cada foto como `productos/c/<Cod.Articulo>.jpg?v=<n>`. Existe una
versión más grande (`productos/m/`), pero no está para todos los productos. Cuando no hay foto, el
sitio muestra la imagen genérica `imagenes/Fispa_imagen.jpg`.

**Decisión.** Se guarda `https://fispaargentina.com.ar/productos/c/<archivo>.jpg`: la primera imagen
del producto, sin el parámetro `?v=`, que solo sirve para refrescar caches. La imagen genérica se
trata como "sin foto": queda vacía y se registra en el log.

**Criterio.** Es la URL que el sitio realmente sirve (se verificaron muestras con respuesta 200
`image/jpeg`). Guardar la imagen genérica haría parecer que el producto tiene foto. Para ser
respetuosos con el servidor se recorren las ~96 páginas de rubro en lugar de ~2.000 fichas, con
1,5 s de pausa y cache local. Solo se consulta la ficha individual de los productos que no aparecen
en ningún rubro.

## D9 — Formatos y carpetas

**Decisión.**
- Salida en CSV UTF-8 con BOM, separado por comas, más SQLite (`base_maestra.sqlite`).
- SOP en Word (.docx).
- Carpetas `entrada/` (3 Excel con nombres fijos) y `salida/`.

**Criterio.**
- El BOM hace que Excel muestre bien los acentos al abrir el CSV con doble clic, y el archivo sigue
  siendo UTF-8 válido.
- SQLite no tiene costo adicional y permite consultas.
- El .docx es editable por el área y se exporta a PDF.
- Los nombres fijos sin espacios evitan errores del personal y simplifican el SOP.

## D10 — Limpieza de Cruces_OEM; Aplicacion_Completa se mantiene intacta

**Contexto.** `Cod.Ref.Aux` trae el prefijo "REF ORIG" en el 80% de las filas, con variantes
(`REF.ORIG`, `REF.ORIG.`, `REF. ORIG`, `REF.ORIG_`, `REF.ORIG:`, `REF ORIGINAL`, `REF ORIGI`,
`REF ORI`, `REF ORlG`, `REF ORG`, `REF OEM`), y mezcla separadores. `Aplicacion` escribe las
cilindradas sin punto ("1 6 16V") en 1.344 filas.

**Opciones.** (a) Normalizar las cilindradas de Aplicacion_Completa ("1 6" → "1.6"); (b) quitar el
prefijo de Cruces_OEM y separar todos los códigos con " | "; (c) quitar el prefijo y unificar solo
los separadores " - " que ya existen.

**Decisión.** (c) para Cruces_OEM. Los valores que eran solo guiones quedan vacíos.

Aplicacion_Completa no se reescribe: las cilindradas quedan como las escribe Fispa ("1 6 16V").
Igual que en el resto de los textos, solo se aplica la limpieza general (`limpiar_texto`), que
hace exactamente esto:
- quita caracteres de control (`_x001F_`);
- colapsa espacios dobles y recorta los extremos;
- repara dos caracteres rotos con evidencia del original (detalle en D11):
  - `O?RINGS` / `OïRINGS` → `O'RINGS`, porque la web de Fispa escribe "KIT FILTROS Y O'RINGS";
  - un `?` aislado entre espacios → ` - `, porque ocupa el lugar de un separador perdido
    (`2005 ? 2016`).

Esa misma limpieza general se aplica también a Cruces_OEM, antes de quitar el prefijo.

**Criterio.**
- La consigna dice que la aplicación detallada "se preserva intacta en la columna técnica
  separada". Por eso la corrección de cilindradas se aplica solo en Descripcion_Optimizada.
- Separar todos los códigos OEM por espacio (opción b) **rompería datos**: hay códigos con espacios
  internos ("D51 84", "77 00 274 008") y marcas delante de sus códigos ("FIAT 7735919"). Decidir
  dónde termina cada código sería una estimación.
- Quitar el prefijo y unificar los separadores existentes no pierde información y mejora la
  lectura y la búsqueda.

**Verificación (01/11/2026, sobre las 3.668 filas de la lista).**
- Contenido alfanumérico del original sin prefijo vs el limpio: **0 diferencias**.
- Filas con distinta cantidad de dígitos antes y después: **0**.
- Ningún valor limpio empieza con restos del prefijo. Un caso empieza con "I-"
  (`I-032-121065-D`), pero es un código real.
- Valores vacíos generados por la limpieza: 24, y los 24 eran solo guiones ("----------").

## D11 — Reparación de caracteres rotos en los textos de Fispa

**Contexto.** La lista del proveedor trae caracteres que se rompieron en su exportación:
- `O?RINGS` / `OïRINGS` (32 filas de Aplicacion_Completa);
- `?` usado como separador (`2005 ? 2016`, `Cummins ? MWM`): 43 filas de Aplicacion_Completa y 1
  de Cruces_OEM;
- otros `?` cuyo original no se puede saber: `1? SERIE`, `Salida ?8`, `50?C`, `23 OHM?`.
También la Categoría del ERP dice `KITS DE FILTROS Y OïRINGS` (45 artículos).

**Opciones.** (a) No tocar nada; (b) reparar solo los casos con evidencia del original;
(c) reemplazar todos los `?` por el carácter más probable (`ª`, `º`, `Ø`, `°`).

**Decisión.** (b):
- `O?RINGS` y `OïRINGS` → `O'RINGS`.
- Un `?` aislado entre espacios → ` - `.
- El resto de los `?` queda como está.
- La Categoría `OïRINGS` **no se modifica**.

**Criterio.**
- La propia web de Fispa escribe "KIT FILTROS Y O'RINGS" y "O´RINGS BOMBAS": el original era un
  apóstrofo.
- Un `?` entre espacios está ocupando el lugar de un separador perdido.
- Reparar estos casos restituye el dato original, no lo reescribe. Es la misma limpieza que se
  hace con `_x001F_`. D10 detalla cómo se aplica en Aplicacion_Completa.
- En cambio, decidir si `1?` era `1ª` o `1º`, o si `?8` era `Ø8` o `°8`, sería inventar datos.
- La Categoría es un campo inmutable del ERP: el carácter roto se corrige en el ERP, no en el
  pipeline.

**Resultado.**

| Columna | Filas con `?` o `ï` antes | Después |
|---|---|---|
| Aplicacion_Completa | 102 | 29 (sin original conocido) |
| Cruces_OEM | 9 | 8 |
| Descripcion_Optimizada | 0 | 0 |
| Categoria | 45 | 45 (inmutable) |
