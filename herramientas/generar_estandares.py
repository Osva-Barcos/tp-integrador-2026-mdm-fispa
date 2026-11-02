"""
Genera el documento para el grupo: docs/Estandares_y_Decisiones.docx

Es el resumen legible de todas las estandarizaciones y decisiones acordadas. El detalle
técnico (criterios completos y verificaciones) sigue en DECISIONES.md y diagnostico_datos.md.
Los números se calculan desde la carpeta salida/, así el documento coincide con la base.

Requiere haber corrido antes el pipeline y tener python-docx.
Uso: python herramientas/generar_estandares.py
"""
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

REPO = Path(__file__).resolve().parent.parent
SALIDA = REPO / "docs" / "Estandares_y_Decisiones.docx"
AZUL = RGBColor(0x1F, 0x4E, 0x79)

# --- Números reales de la última ejecución --------------------------------------------
base = pd.read_csv(REPO / "salida/base_maestra.csv", dtype=str, encoding="utf-8-sig",
                   keep_default_na=False)
errores = pd.read_csv(REPO / "salida/errores_sin_mapeo.csv", dtype=str, encoding="utf-8-sig",
                      keep_default_na=False)
bajo_costo = pd.read_csv(REPO / "salida/precio_menor_costo.csv", encoding="utf-8-sig")
precio = pd.to_numeric(base["Precio"], errors="coerce").fillna(0)
n = lambda x: f"{x:,}".replace(",", ".")
TOTAL = len(base)
CRUZADOS = int((base["Costo_Reposicion"] != "").sum())
EXCEPCIONES = len(errores)
SIN_CODIGO = int((errores["Motivo"] == "SIN_CODIGO_PROVEEDOR").sum())
NO_EN_LISTA = int((errores["Motivo"] == "NO_FIGURA_EN_LISTA_FABRICANTE").sum())
CON_SUGERENCIA = int((errores["Sugerencia_Revision"] != "").sum())
PRECIO_CERO = int((precio == 0).sum())
CON_FOTO = int((base["URL_Foto"] != "").sum())
SIN_FOTO = CRUZADOS - CON_FOTO

# --- Formato -----------------------------------------------------------------------------
doc = Document()
s = doc.sections[0]
s.page_width, s.page_height = Cm(21), Cm(29.7)
s.left_margin = s.right_margin = Cm(1.7)
s.top_margin = s.bottom_margin = Cm(1.5)
st = doc.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(10)
st.paragraph_format.space_after = Pt(3)


def sombrear(celda, color):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    celda._tc.get_or_add_tcPr().append(shd)


def titulo(texto):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(9)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(texto)
    r.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = AZUL


def parrafo(*partes):
    p = doc.add_paragraph()
    for parte in partes:
        r = p.add_run(parte[2:] if parte.startswith("**") else parte)
        r.bold = parte.startswith("**")
    return p


def vineta(*partes, estilo="List Bullet"):
    p = doc.add_paragraph(style=estilo)
    p.paragraph_format.space_after = Pt(1)
    for parte in partes:
        r = p.add_run(parte[2:] if parte.startswith("**") else parte)
        r.bold = parte.startswith("**")


def tabla(encabezados, filas, anchos, tam=8.5, negrita_col0=True):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Table Grid"
    for i, texto in enumerate(encabezados):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(texto)
        r.bold = True
        r.font.size = Pt(tam)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        sombrear(c, "1F4E79")
    for k, fila in enumerate(filas):
        celdas = t.add_row().cells
        for i, texto in enumerate(fila):
            celdas[i].text = ""
            r = celdas[i].paragraphs[0].add_run(texto)
            r.font.size = Pt(tam)
            r.bold = negrita_col0 and i == 0
            if k % 2:
                sombrear(celdas[i], "EEF3F8")
    for fila in t.rows:
        for i, ancho in enumerate(anchos):
            fila.cells[i].width = Cm(ancho)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


# --- Encabezado ----------------------------------------------------------------------------
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("ESTÁNDARES Y DECISIONES — BASE MAESTRA FISPA")
r.bold = True
r.font.size = Pt(15)
r.font.color.rgb = AZUL
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Práctico Integrador 2026 · Fase previa común (MDM / ETL) · Sistemas de Gestión · UTN FRSF")
r.italic = True
r.font.size = Pt(9)

# --- 1 -----------------------------------------------------------------------------------------
titulo("1. Para qué sirve este documento")
parrafo("Es el acuerdo del grupo sobre cómo se arma y se estandariza la Base Maestra: qué se hace "
        "con cada columna, qué reglas generales se respetan y por qué se tomó cada decisión. "
        "Ante un caso nuevo, primero se busca acá; si no está, se propone una regla nueva "
        "(sección 6). El detalle técnico completo de cada criterio, con sus verificaciones, está "
        "en ", "**04_Pipeline/docs/DECISIONES.md", " y ", "**diagnostico_datos.md", ".")
parrafo(f"Situación actual: {n(TOTAL)} artículos activos, {n(CRUZADOS)} cruzados con la lista de "
        f"Fispa y {n(EXCEPCIONES)} excepciones, que figuran en errores_sin_mapeo.csv.")

# --- 2 -----------------------------------------------------------------------------------------
titulo("2. Estándar por columna")
tabla(["Columna", "De dónde sale", "Qué se le hace", "Qué NO se hace"], [
    ["Codigo_Interno", "ERP · Compras", "Se copia tal cual", "Nunca se modifica (clave del ERP)"],
    ["Marca", "ERP · Compras", "Se copia tal cual", "Nunca se modifica"],
    ["Categoria", "ERP · Compras", "Se copia tal cual", "Nunca se modifica, ni siquiera para "
                                                          "corregir “OïRINGS”"],
    ["Codigo_Proveedor", "ERP · Compras", "Se quitan espacios sobrantes", "No se reformatea "
                                                                           "(guiones y letras quedan)"],
    ["Descripcion_Optimizada", "Generada",
     "Tipo de pieza de Fispa + aplicación del ERP. Máximo 90 caracteres, MAYÚSCULAS, sin la "
     "marca del artículo, sin códigos de 6 o más dígitos, cilindradas con punto (1.6), sin "
     "conector al final", "No se corrigen errores de tipeo del ERP ni se agrega texto inventado"],
    ["Precio", "ERP · Ventas", "Número con punto decimal", "No se corrige: si es 0 o menor al "
                                                            "costo, se avisa"],
    ["Costo_Reposicion", "Fispa · Importe", "Número con punto decimal", "Queda vacío si el "
                                                                         "artículo no cruza"],
    ["EAN13", "Fispa · CodigoBarras", "Se carga solo si es un EAN-13 válido (13 dígitos + "
                                      "dígito verificador)", "No se copia otro código: hoy queda "
                                                             "vacío"],
    ["Cruces_OEM", "Fispa · Cod.Ref.Aux", "Se quita “REF ORIG” y “OEM” del comienzo; los "
                                          "separadores “ - ” pasan a “ | ”",
     "No se parten códigos ni se borran las notas que carga Fispa"],
    ["Aplicacion_Completa", "Fispa · Aplicacion", "Solo limpieza mínima: caracteres de control, "
                                                  "espacios dobles y “O?RINGS” → “O'RINGS”",
     "No se reescribe (la consigna pide dejarla intacta)"],
    ["URL_Foto", "Web de Fispa", "URL directa de la imagen publicada (productos/c/…jpg)",
     "Queda vacía si el sitio muestra la imagen genérica"],
], [3.3, 2.8, 6.3, 5.2])

# --- 3 -----------------------------------------------------------------------------------------
titulo("3. Reglas generales que respetamos")
for partes in [
    ("**Inmutables: ", "Código interno, Marca y Categoría se copian del ERP sin cambios."),
    ("**El universo lo define el ERP: ", f"entran los {n(TOTAL)} artículos activos. Los artículos "
     "de la lista de Fispa que la empresa no vende quedan afuera."),
    ("**Cruce exacto: ", "un artículo recibe datos de Fispa solo si su código de proveedor es "
     "igual al de la lista (solo se ignoran espacios y mayúsculas). Nada aproximado. Las "
     "sugerencias del log son solo para revisión humana."),
    ("**Reproducible: ", "con los mismos archivos, el proceso da siempre el mismo resultado. "
     "No se usa inteligencia artificial."),
    ("**No inventar datos: ", "si un dato no existe o no es válido, queda vacío y se informa."),
    ("**Reparar solo con evidencia: ", "un carácter roto se corrige solo si se sabe cuál era "
     "(por ejemplo, la web de Fispa escribe O'RINGS)."),
    ("**Los datos comerciales no se corrigen: ", "precios en cero o por debajo del costo se "
     "avisan para que los revise Comercial."),
    ("**Los errores del origen se corrigen en el origen: ", "en el ERP o pidiéndoselo a Fispa, "
     "no en el proceso."),
    ("**Formato de salida: ", "CSV UTF-8 separado por comas, con las 11 columnas del Anexo 2 en "
     "orden, más una copia en SQLite."),
    ("**Toda regla nueva se registra ", "en este documento antes de aplicarla (sección 6)."),
]:
    vineta(*partes)

# --- 4 -----------------------------------------------------------------------------------------
titulo("4. Decisiones tomadas")
tabla(["N°", "Qué decidimos", "Por qué"], [
    ["D1", f"La base tiene los {n(TOTAL)} artículos. Los {EXCEPCIONES} sin cruce quedan sin datos "
           "de Fispa y van al log de excepciones",
     "La consigna pide los 2.184 registros; sacar artículos activos los ocultaría para la venta"],
    ["D2", "EAN13 queda vacío y se carga solo si llega un EAN-13 válido. La columna no se elimina",
     "Ningún código de barras de Fispa es EAN-13; copiar otro dato sería falso. El Anexo 2 exige "
     "la columna"],
    ["D3", "La descripción se arma con 14 reglas fijas", "Es reproducible, gratis, sin API y cada "
                                                         "resultado se puede explicar"],
    ["D4", "Cruce exacto: solo se ignoran espacios y mayúsculas", "Sigue siendo 1 a 1; normalizar "
                                                                  "más no suma cruces"],
    ["D5", "Se usan Cod.Ref.Aux y Aplicacion (las columnas del Anexo 2)", "Sus copias en la lista "
                                                                         "son idénticas al 100%"],
    ["D6", "Si dos artículos comparten código de proveedor, se enriquecen ambos y se avisa",
     "El ERP no se toca; Compras lo revisa"],
    ["D7", "El log sugiere posibles equivalentes, pero nunca se usan para cruzar",
     "Ayuda a corregir sin estimar"],
    ["D8", "La foto es la URL publicada en el sitio; la imagen genérica cuenta como “sin foto”",
     "Es la que el sitio realmente muestra"],
    ["D9", "CSV UTF-8 + SQLite, SOP en Word, carpetas entrada/ y salida/", "Excel muestra bien "
                                                                          "los acentos; nombres "
                                                                          "fijos evitan errores"],
    ["D10", "Cruces_OEM sin prefijos y con separador “ | ”; Aplicacion_Completa intacta",
     "No se pierde ningún código (verificado); la consigna pide la aplicación intacta"],
    ["D11", "Los caracteres rotos se reparan solo si se conoce el original", "Elegir entre ª, º "
                                                                             "u Ø sería inventar"],
    ["D12", "Alarma de precio menor al costo, sin corregir nada", "Con estos datos no se puede "
                                                                  "saber la causa"],
], [1.1, 8.3, 8.2])

# --- 5 -----------------------------------------------------------------------------------------
titulo("5. Lo que encontramos en los datos y quién lo resuelve")
tabla(["Hallazgo", "Cantidad", "Quién lo resuelve"], [
    ["Artículos sin código de proveedor en el ERP", n(SIN_CODIGO), "Compras (cargar el código)"],
    ["Códigos de proveedor que no están en la lista de Fispa", f"{n(NO_EN_LISTA)} ({CON_SUGERENCIA} "
     "con posible equivalente)", "Compras, consultando a Fispa"],
    ["Precios en cero", n(PRECIO_CERO), "Comercial (corregir en el ERP)"],
    ["Precio de venta menor al costo de reposición", n(len(bajo_costo)), "Comercial (ver "
                                                                         "precio_menor_costo.csv)"],
    ["Códigos de proveedor compartidos por dos artículos", "2 pares", "Compras"],
    ["Nombre que contradice a Fispa (12014: “rotación” vs “detonación”)", "1", "Compras"],
    ["Categoría con carácter roto (“OïRINGS”)", "45", "Corregir en el ERP"],
    ["Códigos de barras que no son EAN-13", "Todos", "Pedírselos a Fispa"],
    ["Artículos cruzados sin foto en la web de Fispa", n(SIN_FOTO), "Fispa"],
    ["Errores de tipeo en nombres del ERP (TOYOYA, REGUALDOR…)", "Varios", "Corregir en el ERP"],
    ["Notas y especificaciones mezcladas en las referencias OEM", "13% de las celdas",
     "Informativo (texto libre de Fispa)"],
], [9.2, 3.3, 5.1], negrita_col0=False)

# --- 6 -----------------------------------------------------------------------------------------
titulo("6. Cómo proponer un cambio")
for paso in [
    "Describir el caso con ejemplos reales y cuántos artículos afecta.",
    "Proponer la regla y su criterio: por qué es correcta y qué riesgo tiene.",
    "Acordarlo en el grupo.",
    "Registrarlo como D13 (o la que siga) en este documento y en DECISIONES.md.",
    "Aplicarlo en el proceso y verificar que solo cambian los artículos esperados.",
    "Regenerar la entrega.",
]:
    vineta(paso, estilo="List Number")

doc.save(SALIDA)
print(f"Documento generado: {SALIDA}")
