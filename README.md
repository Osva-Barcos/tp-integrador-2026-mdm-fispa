# Base Maestra Normalizada Fispa — Pipeline ETL / MDM

Práctico Integrador 2026 · Sistemas de Gestión · UTN FRSF
Fase previa común: Ingeniería de datos y automatización (MDM / ETL).

Pipeline automatizado que genera el **Golden Record** de los 2.184 artículos activos de la marca
Fispa:

- une el reporte de Ventas (ERP1) y el de Compras (ERP2);
- cruza de forma determinista con la lista del fabricante;
- genera una descripción comercial optimizada;
- obtiene la URL de la foto oficial desde fispaargentina.com.ar.

## Uso rápido (personal administrativo)

1. Guardar los 3 Excel en `entrada/` con estos nombres: `erp1_ventas.xlsx`, `erp2_compras.xlsx`,
   `lista_proveedor.xlsx`.
2. Doble clic en **`ejecutar_pipeline.bat`**.
3. Revisar `salida/control_calidad.txt` y `salida/errores_sin_mapeo.csv`.

El paso a paso completo está en el SOP: [`docs/SOP_Actualizacion_Base_Maestra.docx`](docs/SOP_Actualizacion_Base_Maestra.docx).

El `.bat` busca Python. La primera vez crea un entorno virtual (`.venv`) e instala
`requirements.txt`; después ejecuta el proceso y abre la carpeta `salida`. Solo requiere tener
**Python 3.10+** instalado.

## Uso desde consola (desarrolladores)

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python src\pipeline.py              # normal (consulta la web, usa cache)
.venv\Scripts\python src\pipeline.py --sin-fotos  # sin conexión: solo usa la cache
```

## Entregables

| Archivo | Contenido |
|---|---|
| `salida/base_maestra.csv` | Golden Record: 2.184 filas, UTF-8, separado por comas, columnas del Anexo 2 en orden |
| `salida/base_maestra.sqlite` | La misma base (tabla `base_maestra`) más la tabla `errores_sin_mapeo` |
| `salida/errores_sin_mapeo.csv` | Artículos sin código de proveedor o que no figuran en la lista, con motivo y sugerencia de revisión |
| `salida/control_calidad.txt` | Verificaciones automáticas y precios en cero |
| `salida/log_proceso.txt` | Detalle de la ejecución, avisos y productos sin foto |
| `salida/precio_menor_costo.csv` | Alarma: artículos con precio menor al costo de reposición de Fispa (D12) |
| `docs/SOP_Actualizacion_Base_Maestra.docx` | Procedimiento para personal administrativo (se regenera con `python docs/generar_sop.py`, requiere `python-docx`) |
| `docs/DECISIONES.md` | Decisiones de diseño con su criterio |
| `docs/armar_entrega.py` | Arma la carpeta de entrega y su `.zip` a partir de `salida/` y `docs/` (`python docs/armar_entrega.py`, requiere `python-docx`) |
| `docs/diagnostico_datos.md` | Diagnóstico de calidad de las fuentes |

### Columnas de la base maestra (Anexo 2)

| Columna | Origen |
|---|---|
| Codigo_Interno, Marca, Categoria | ERP2, copiados sin modificar (inmutables) |
| Codigo_Proveedor | ERP2 `Codigo Proveedor` (sin espacios sobrantes) |
| Descripcion_Optimizada | Generada por reglas (`src/descripcion.py`), máximo 90 caracteres |
| Precio | ERP1 `Precio` |
| Costo_Reposicion | Fispa `Importe` |
| EAN13 | Fispa `CodigoBarras`, solo si es un EAN-13 válido (hoy ninguno lo es, ver D2) |
| Cruces_OEM | Fispa `Cod.Ref.Aux`, sin el prefijo "REF ORIG" y con los separadores unificados como barra vertical (ver D10) |
| Aplicacion_Completa | Fispa `Aplicacion` |
| URL_Foto | Scraping de fispaargentina.com.ar |

## Estructura de carpetas

| Carpeta | Contenido |
|---|---|
| `fuentes_originales/` | Archivos tal como los entregó la cátedra (consigna y las 3 planillas con sus nombres originales). No se modifican |
| `entrada/` | Copias de los Excel con los nombres fijos que lee el pipeline (las reemplaza el administrativo en cada actualización) |
| `salida/` | Resultados generados |
| `src/` | Código del pipeline |
| `docs/` | SOP, decisiones y diagnóstico |
| `cache/` | Páginas del sitio de Fispa ya descargadas (se regenera sola) |

## Arquitectura

```
entrada/ (3 Excel) ──► extraer.py ──► transformar.py ──► descripcion.py ──► cargar.py ──► salida/
                                         │                  scraper.py ─┘        │
                                         └── excepciones ──────────────────────► controles.py
```

| Módulo | Responsabilidad |
|---|---|
| `src/config.py` | Rutas, nombres de archivo, columnas esperadas, parámetros del scraper |
| `src/extraer.py` | Lectura de los Excel como texto, detección del encabezado de la lista, validación de columnas, conversión de precios (incluido el formato argentino) |
| `src/transformar.py` | Unión ERP1+ERP2, clave de cruce, cruce con la lista (left join validado), excepciones, sugerencias, validación EAN-13 |
| `src/descripcion.py` | Reglas de Descripcion_Optimizada |
| `src/scraper.py` | Fotos: páginas de rubro y ficha individual como respaldo, con pausa, reintentos y cache en `cache/` |
| `src/cargar.py` | Escritura de CSV y SQLite |
| `src/controles.py` | Controles de calidad y `control_calidad.txt` |
| `src/pipeline.py` | Orquestador y log |

## Resultados de la última ejecución (01/11/2026)

| Control | Resultado |
|---|---|
| Filas de la base | 2.184 |
| Cruzados + excepciones | 2.042 + 142 = 2.184 ✔ |
| Excepciones | 141 no figuran en la lista, 1 sin código de proveedor (9 con sugerencia de revisión) |
| Código, Marca y Categoría vs ERP | Idénticos en el 100% de las filas |
| Descripción | máx 90, promedio 71, 1.320 entre 70 y 90, todo en mayúsculas, sin códigos OEM ni "FISPA" |
| Precios en cero | 9 (todos entre los no cruzados; listados en control_calidad.txt) |
| Precio menor al costo | 522 artículos (aviso, lista en precio_menor_costo.csv) |
| Fotos | 2.028 SKU con foto; 14 artículos Fispa sin foto en el sitio |
| EAN-13 válidos | 0 (la fuente no los trae) |

## Reglas de negocio garantizadas

- **Inmutabilidad:** Código interno, Marca y Categoría se copian literalmente del ERP y se
  verifican celda por celda en cada corrida.
- **Cruce determinista:** igualdad exacta de clave (solo trim y mayúsculas). Se valida la unicidad
  y no hay fuzzy matching. Las sugerencias del log nunca se usan para cruzar.
- **Filtro de demanda:** solo los SKU activos del ERP; los artículos del proveedor que la empresa no
  vende quedan fuera.
