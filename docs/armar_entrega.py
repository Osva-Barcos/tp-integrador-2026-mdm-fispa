"""
Arma la carpeta de entrega (y su .zip) a partir del contenido del repo, sin modificarlo.

Genera Entrega_TP_Integrador_2026_Fispa/ con:
  00_LEEME.docx · 01_Base_Maestra · 02_Log_Excepciones · 03_SOP · 04_Pipeline ·
  05_Documentacion_Tecnica (Decisiones y Diagnóstico convertidos a .docx)

Requiere haber corrido antes el pipeline (usa la carpeta salida/) y tener python-docx.
Uso: python docs/armar_entrega.py
"""
import re
import shutil
from pathlib import Path

import pandas as pd
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

REPO = Path(__file__).resolve().parent.parent   # carpeta raíz del proyecto
DEST = REPO / "Entrega_TP_Integrador_2026_Fispa"
AZUL = RGBColor(0x1F, 0x4E, 0x79)

if DEST.exists():
    shutil.rmtree(DEST)
for sub in ["01_Base_Maestra", "02_Log_Excepciones", "03_SOP", "04_Pipeline",
            "05_Documentacion_Tecnica"]:
    (DEST / sub).mkdir(parents=True)

# --- 01, 02, 03 ---------------------------------------------------------------
shutil.copy2(REPO / "salida/base_maestra.csv", DEST / "01_Base_Maestra")
shutil.copy2(REPO / "salida/base_maestra.sqlite", DEST / "01_Base_Maestra")
shutil.copy2(REPO / "salida/errores_sin_mapeo.csv", DEST / "02_Log_Excepciones")
shutil.copy2(REPO / "docs/SOP_Actualizacion_Base_Maestra.docx", DEST / "03_SOP")

# --- 04 Pipeline: copia ejecutable del proyecto -----------------------------------
p = DEST / "04_Pipeline"
for f in ["ejecutar_pipeline.bat", "requirements.txt", "README.md", ".gitignore"]:
    shutil.copy2(REPO / f, p)
shutil.copytree(REPO / "src", p / "src", ignore=shutil.ignore_patterns("__pycache__"))
shutil.copytree(REPO / "entrada", p / "entrada")
shutil.copytree(REPO / "docs", p / "docs", ignore=shutil.ignore_patterns("__pycache__"))
shutil.copytree(REPO / "fuentes_originales", p / "fuentes_originales")


# --- utilidades docx ------------------------------------------------------------------
def nuevo_doc():
    d = Document()
    s = d.sections[0]
    s.page_width, s.page_height = Cm(21), Cm(29.7)
    s.left_margin = s.right_margin = Cm(2)
    s.top_margin = s.bottom_margin = Cm(1.8)
    st = d.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)
    st.paragraph_format.space_after = Pt(3)
    for nivel, tam in ((1, 16), (2, 13), (3, 11)):
        h = d.styles[f"Heading {nivel}"]
        h.font.color.rgb = AZUL
        h.font.size = Pt(tam)
        h.font.name = "Calibri"
    return d


def sombrear(celda, color):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    celda._tc.get_or_add_tcPr().append(shd)


def runs(par, texto, tam=None):
    """Escribe texto con **negrita** y `código` de markdown."""
    for parte in re.split(r"(\*\*.+?\*\*|`.+?`)", texto):
        if not parte:
            continue
        if parte.startswith("**"):
            r = par.add_run(parte[2:-2]); r.bold = True
        elif parte.startswith("`"):
            r = par.add_run(parte[1:-1]); r.font.name = "Consolas"
        else:
            r = par.add_run(parte)
        if tam:
            r.font.size = Pt(tam)


def tabla(d, filas):
    t = d.add_table(rows=0, cols=len(filas[0]))
    t.style = "Table Grid"
    for n, fila in enumerate(filas):
        celdas = t.add_row().cells
        for i, txt in enumerate(fila):
            celdas[i].text = ""
            runs(celdas[i].paragraphs[0], txt, 9)
            if n == 0:
                for r in celdas[i].paragraphs[0].runs:
                    r.bold = True
                    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                sombrear(celdas[i], "1F4E79")
    d.add_paragraph()


def md_a_docx(origen, destino):
    """Conversor simple de markdown (títulos, párrafos, listas, tablas, bloques de código)."""
    d = nuevo_doc()
    lineas = origen.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lineas):
        l = lineas[i]
        if l.startswith("```"):
            i += 1
            while i < len(lineas) and not lineas[i].startswith("```"):
                r = d.add_paragraph().add_run(lineas[i]); r.font.name = "Consolas"; r.font.size = Pt(8.5)
                i += 1
        elif l.startswith("|"):
            filas = []
            while i < len(lineas) and lineas[i].startswith("|"):
                celdas = [c.strip() for c in re.split(r"(?<!\\)\|", lineas[i].strip()[1:-1])]
                if not all(re.fullmatch(r":?-+:?", c) for c in celdas):
                    filas.append([c.replace("\\|", "|") for c in celdas])
                i += 1
            tabla(d, filas)
            continue
        elif m := re.match(r"^(#{1,3}) (.*)", l):
            d.add_heading(m.group(2).replace("`", ""), level=len(m.group(1)))
        elif re.match(r"^\s*- ", l):
            runs(d.add_paragraph(style="List Bullet"), re.sub(r"^\s*- ", "", l))
        elif re.match(r"^\d+\. ", l):
            runs(d.add_paragraph(style="List Number"), re.sub(r"^\d+\. ", "", l))
        elif l.strip() in ("", "---"):
            pass
        else:
            texto = l
            while i + 1 < len(lineas) and lineas[i + 1].strip() and not re.match(
                    r"^(#|\||- |\s+- |\d+\. |```|---)", lineas[i + 1]):
                i += 1
                texto += " " + lineas[i].strip()
            texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)  # links -> texto
            runs(d.add_paragraph(), texto)
        i += 1
    d.save(destino)


# --- 05 Documentación técnica -------------------------------------------------------
doc5 = DEST / "05_Documentacion_Tecnica"
md_a_docx(REPO / "docs/DECISIONES.md", doc5 / "Decisiones_de_diseno.docx")
md_a_docx(REPO / "docs/diagnostico_datos.md", doc5 / "Diagnostico_de_datos.docx")
shutil.copy2(REPO / "salida/control_calidad.txt", doc5)
shutil.copy2(REPO / "salida/log_proceso.txt", doc5)

# --- 00_LEEME.docx --------------------------------------------------------------------
base = pd.read_csv(REPO / "salida/base_maestra.csv", dtype=str, encoding="utf-8-sig",
                   keep_default_na=False)
err = pd.read_csv(REPO / "salida/errores_sin_mapeo.csv", dtype=str, encoding="utf-8-sig",
                  keep_default_na=False)
largos = base["Descripcion_Optimizada"].str.len()
precios0 = int((pd.to_numeric(base["Precio"], errors="coerce").fillna(0) == 0).sum())
con_foto = int((base["URL_Foto"] != "").sum())
motivos = err["Motivo"].value_counts().to_dict()

d = nuevo_doc()
d.add_heading("Práctico Integrador 2026 — Fase previa común", level=1)
runs(d.add_paragraph(), "**Ingeniería de datos y automatización (MDM / ETL)** · Sistemas de Gestión · UTN FRSF")
runs(d.add_paragraph(), "Base Maestra Normalizada (Golden Record) de los 2.184 artículos activos de la marca "
     "Fispa, generada por un pipeline ETL automatizado.")

d.add_heading("Contenido de la entrega", level=2)
tabla(d, [
    ["Carpeta", "Contenido", "Entregable de la consigna"],
    ["01_Base_Maestra", "`base_maestra.csv` (UTF-8, separado por comas) y `base_maestra.sqlite`, "
     "columnas del Anexo 2", "Entregable 1"],
    ["02_Log_Excepciones", "`errores_sin_mapeo.csv`: artículos sin código de proveedor o que no figuran "
     "en la lista del fabricante, con motivo y sugerencia de revisión", "Entregable 2"],
    ["03_SOP", "`SOP_Actualizacion_Base_Maestra.docx`: procedimiento para personal administrativo "
     "(Anexo 3)", "Entregable 3"],
    ["04_Pipeline", "Programa completo listo para ejecutar: `ejecutar_pipeline.bat`, código en `src/`, "
     "archivos de `entrada/`, `requirements.txt`, `README.md`", "Pipeline automatizado (objetivo central)"],
    ["05_Documentacion_Tecnica", "Decisiones de diseño con su criterio, diagnóstico de los datos, "
     "control de calidad y log de la última ejecución", "Respaldo para la defensa"],
])

d.add_heading("Resultados de la última ejecución", level=2)
tabla(d, [
    ["Control", "Resultado"],
    ["Artículos en la base maestra", f"{len(base):,}".replace(",", ".")],
    ["Cruzados con la lista de Fispa + excepciones",
     f"{len(base) - len(err):,} + {len(err)} = {len(base):,}".replace(",", ".")],
    ["Excepciones por motivo", " · ".join(f"{k}: {v}" for k, v in motivos.items())],
    ["Código interno, Marca y Categoría", "Idénticos al ERP en el 100% de las filas"],
    ["Descripcion_Optimizada", f"máx {largos.max()} caracteres · promedio {largos.mean():.0f} · "
     f"{int(((largos >= 70) & (largos <= 90)).sum()):,} entre 70 y 90 · ninguna repite FISPA".replace(",", ".")],
    ["Precios en cero", f"{precios0} (listados en control_calidad.txt; corregir en el ERP)"],
    ["Artículos con foto oficial", f"{con_foto:,}".replace(",", ".")],
    ["EAN-13 válidos", "0 (la lista de Fispa no trae códigos EAN-13 válidos; ver decisión D2)"],
])

d.add_heading("Cómo volver a ejecutar el proceso", level=2)
for paso in ["Descargar la carpeta **04_Pipeline** completa a una PC con Windows y Python 3.10 o superior.",
             "Dejar los 3 Excel en `04_Pipeline\\entrada` con los nombres `erp1_ventas.xlsx`, "
             "`erp2_compras.xlsx` y `lista_proveedor.xlsx` (ya están cargados los de esta entrega).",
             "Doble clic en `ejecutar_pipeline.bat`. La primera vez instala lo necesario y busca las fotos en "
             "la web de Fispa (unos 5 minutos).",
             "Los resultados quedan en `04_Pipeline\\salida`. Revisar `control_calidad.txt`."]:
    runs(d.add_paragraph(style="List Number"), paso)

d.add_heading("Decisiones principales (detalle en 05_Documentacion_Tecnica)", level=2)
for txt in ["**D1** · La base incluye los 2.184 SKU activos; los 142 no cruzados quedan sin datos de Fispa y "
            "figuran en el log de excepciones.",
            "**D2** · EAN13 vacío: ningún CodigoBarras de la lista es un EAN-13 válido.",
            "**D3** · Descripcion_Optimizada generada por reglas deterministas (sin IA), en mayúsculas "
            "y sin códigos OEM.",
            "**D4** · Cruce exacto, solo con espacios recortados y mayúsculas, sin fuzzy matching.",
            "**D8** · Fotos obtenidas de las páginas de rubro del sitio oficial, con pausas y cache.",
            "**D10** · Cruces_OEM sin el prefijo \"REF ORIG\"; Aplicacion_Completa intacta.",
            "**D11** · Caracteres rotos reparados solo cuando se conoce el original (O?RINGS → O'RINGS)."]:
    runs(d.add_paragraph(style="List Bullet"), txt)
d.save(DEST / "00_LEEME.docx")

# --- ZIP ------------------------------------------------------------------------------
zip_ruta = shutil.make_archive(str(DEST), "zip", root_dir=DEST.parent, base_dir=DEST.name)
print("Carpeta:", DEST)
print("ZIP:", zip_ruta)
