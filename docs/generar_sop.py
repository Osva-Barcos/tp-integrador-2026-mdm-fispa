"""
Genera el SOP (Procedimiento Operativo Estándar) en Word: docs/SOP_Actualizacion_Base_Maestra.docx

Se genera por código para que el documento se pueda regenerar si cambian nombres de
archivos o carpetas. Requiere: pip install python-docx
Uso: python docs/generar_sop.py
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

SALIDA = Path(__file__).resolve().parent / "SOP_Actualizacion_Base_Maestra.docx"
AZUL = RGBColor(0x1F, 0x4E, 0x79)

doc = Document()
seccion = doc.sections[0]
seccion.page_width, seccion.page_height = Cm(21), Cm(29.7)   # A4
seccion.left_margin = seccion.right_margin = Cm(1.8)
seccion.top_margin = seccion.bottom_margin = Cm(1.5)

estilo = doc.styles["Normal"]
estilo.font.name = "Calibri"
estilo.font.size = Pt(10)
estilo.paragraph_format.space_after = Pt(2)
estilo.paragraph_format.space_before = Pt(0)


def sombrear(celda, color):
    tcPr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def titulo(texto, tamano=12):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(7)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(texto)
    r.bold = True
    r.font.size = Pt(tamano)
    r.font.color.rgb = AZUL
    return p


def parrafo(*partes):
    """partes: textos; los que empiezan con '**' se escriben en negrita."""
    p = doc.add_paragraph()
    for parte in partes:
        if parte.startswith("**"):
            p.add_run(parte[2:]).bold = True
        else:
            p.add_run(parte)
    return p


def vineta(*partes, estilo_lista="List Bullet"):
    p = doc.add_paragraph(style=estilo_lista)
    p.paragraph_format.space_after = Pt(1)
    for parte in partes:
        if parte.startswith("**"):
            p.add_run(parte[2:]).bold = True
        else:
            p.add_run(parte)
    return p


def tabla(encabezados, filas, anchos):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, texto in enumerate(encabezados):
        celda = t.rows[0].cells[i]
        celda.text = ""
        r = celda.paragraphs[0].add_run(texto)
        r.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        sombrear(celda, "1F4E79")
    for fila in filas:
        celdas = t.add_row().cells
        for i, texto in enumerate(fila):
            celdas[i].text = ""
            r = celdas[i].paragraphs[0].add_run(texto)
            r.font.size = Pt(9)
            if i == len(fila) - 1 and texto.endswith(".xlsx"):
                r.bold = True
    for fila in t.rows:
        for i, ancho in enumerate(anchos):
            fila.cells[i].width = Cm(ancho)
    return t


# ---------------------------------------------------------------------------
# Encabezado
# ---------------------------------------------------------------------------
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("PROCEDIMIENTO OPERATIVO ESTÁNDAR (SOP)")
r.bold = True
r.font.size = Pt(15)
r.font.color.rgb = AZUL
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Actualización de la Base Maestra de artículos Fispa")
r.bold = True
r.font.size = Pt(12)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Práctico Integrador 2026 · Sistemas de Gestión · UTN FRSF")
r.italic = True
r.font.size = Pt(9)

parrafo("Este procedimiento describe cómo actualizar la ", "**Base Maestra de artículos Fispa",
        ", la planilla única que alimenta la tienda online, la atención por WhatsApp y las "
        "publicaciones en redes. El proceso une los precios del área de Ventas, los datos del "
        "Maestro de Artículos de Compras y la lista de precios del fabricante, y suma la foto "
        "oficial de cada producto.")
parrafo("Se realiza cada vez que llega una nueva lista de precios de Fispa o cuando hay cambios de "
        "precios o artículos en el sistema. Lleva alrededor de 15 minutos y solo hace falta acceso "
        "al sistema, a la carpeta compartida y conexión a internet.")

# ---------------------------------------------------------------------------
titulo("PASO 1 · Extracción de los reportes")
parrafo("Desde el sistema se exportan a Excel (.xlsx) los dos reportes de artículos de la marca "
        "Fispa. A eso se suma la lista de precios que envía el fabricante por correo. Cada archivo "
        "necesita, como mínimo, las siguientes columnas con estos mismos títulos en la primera fila:")
tabla(["Archivo", "Origen", "Columnas mínimas (título exacto)", "Se guarda como"],
      [["Reporte de Ventas", "Sistema › Ventas / Precios", "Código · Producto/Nombre · Precio",
        "erp1_ventas.xlsx"],
       ["Reporte de Compras", "Sistema › Maestro de Artículos",
        "Código · Marca · Categoría · Codigo Proveedor", "erp2_compras.xlsx"],
       ["Lista del fabricante", "Correo de Fispa",
        "Cod.Rubro · Rubro · Cod.Articulo · Descripcion · Importe · CodigoBarras · Cod.Ref.Aux · "
        "Aplicacion", "lista_proveedor.xlsx"]],
      [3.2, 4.0, 6.4, 3.8])
vineta("Los títulos de las columnas tienen que quedar tal como los exporta el sistema, y el archivo "
       "no debe incluir filas de totales. Si el reporte trae columnas adicionales no hay problema: "
       "el proceso las ignora.")
vineta("La lista de Fispa suele venir con un título y la fecha en las primeras filas. Se puede dejar "
       "así, porque el proceso encuentra solo dónde empiezan los datos.")

# ---------------------------------------------------------------------------
titulo("PASO 2 · Preparación de la carpeta")
parrafo("Los tres archivos se guardan en la subcarpeta ", "**entrada", ", dentro de la carpeta "
        "compartida ", "**BaseMaestraFispa", " (la misma donde está el archivo "
        "ejecutar_pipeline.bat), con los nombres indicados en el paso anterior:")
vineta("BaseMaestraFispa\\entrada\\erp1_ventas.xlsx")
vineta("BaseMaestraFispa\\entrada\\erp2_compras.xlsx")
vineta("BaseMaestraFispa\\entrada\\lista_proveedor.xlsx")
parrafo("Si Windows avisa que ya existen archivos con ese nombre, se reemplazan: son los de la "
        "actualización anterior. Antes de seguir conviene cerrar los tres archivos en Excel.")

# ---------------------------------------------------------------------------
titulo("PASO 3 · Ejecución del proceso")
vineta("Se hace ", "**doble clic en ejecutar_pipeline.bat", ", dentro de la carpeta "
       "BaseMaestraFispa.", estilo_lista="List Number")
vineta("Se abre una ventana que va mostrando el avance. Hay que dejarla abierta hasta que termine. "
       "La primera vez demora unos minutos más, porque prepara el programa y descarga las fotos "
       "desde la web de Fispa.", estilo_lista="List Number")
vineta("Al finalizar aparece el mensaje ", "**PROCESO TERMINADO CORRECTAMENTE", " y se abre "
       "automáticamente la carpeta ", "**salida", " con los resultados. La ventana se cierra con "
       "cualquier tecla.", estilo_lista="List Number")
tabla(["Archivo en la carpeta salida", "Qué contiene"],
      [["base_maestra.csv", "La Base Maestra lista para publicar. Se abre desde Google Drive o, en "
                            "Excel, desde Datos › Desde texto/CSV (con doble clic puede verse todo "
                            "en una sola columna)."],
       ["control_calidad.txt", "Resumen de los controles automáticos. Es lo primero que se lee "
                               "antes de distribuir."],
       ["errores_sin_mapeo.csv", "Artículos que no pudieron unirse con la lista de Fispa y el motivo."],
       ["log_proceso.txt", "Detalle completo del proceso, incluidos los productos sin foto."]],
      [5.2, 12.2])

# ---------------------------------------------------------------------------
titulo("PASO 4 · Control de calidad antes de distribuir")
vineta("**control_calidad.txt: ", "todas las líneas tienen que figurar como [OK] o [INFO], y al "
       "final debe leerse “Sin errores graves”. Si en cambio aparece “NO DISTRIBUIR”, la base no "
       "se publica y se avisa a Sistemas.")
vineta("**Precios en cero: ", "cuando el control muestra “[REVISAR] artículos con precio en CERO”, "
       "al final del mismo archivo figura la lista de códigos afectados. Esos precios se corrigen en "
       "el sistema, se vuelve a exportar el Reporte de Ventas y se repiten los pasos 2 y 3. Una base "
       "con precios en cero no se publica.")
vineta("**errores_sin_mapeo.csv: ", "la columna Motivo indica por qué cada artículo no pudo unirse "
       "con la lista del fabricante:")
tabla(["Motivo", "Qué significa", "Cómo se resuelve"],
      [["SIN_CODIGO_PROVEEDOR", "El artículo no tiene cargado el código de Fispa en el sistema.",
        "Compras carga el código en el Maestro de Artículos."],
       ["NO_FIGURA_EN_LISTA_FABRICANTE",
        "El código cargado no existe en la lista de Fispa (artículo discontinuado o mal cargado).",
        "Se consulta con Compras o con Fispa. Si aparece un “Posible equivalente”, se verifica "
        "antes de corregir el código."]],
      [5.0, 6.2, 6.2])
vineta("Estos artículos igualmente forman parte de la base maestra, con su precio pero sin costo, "
       "aplicación ni foto. El proceso nunca completa códigos por aproximación: toda corrección se "
       "hace en el sistema.")
vineta("**Fotos: ", "las líneas “Sin foto” de log_proceso.txt indican qué productos quedan "
       "publicados sin imagen.")
vineta("Por último, se recorre rápidamente base_maestra.csv (descripciones, precios y fotos) y, si "
       "todo está en orden, se distribuye.")

# ---------------------------------------------------------------------------
titulo("Si algo sale mal")
tabla(["Mensaje en la ventana", "Cómo se resuelve"],
      [["“No se encontró el archivo …”", "Revisar que el archivo tenga el nombre exacto y esté dentro de la carpeta entrada."],
       ["“Al archivo … le faltan estas columnas …”", "Exportar nuevamente el reporte incluyendo esas columnas (Paso 1)."],
       ["“… probablemente está abierto en Excel”", "Cerrar los archivos de la carpeta salida y volver a ejecutar."],
       ["“No se encontró Python …” o falla la instalación", "Contactar a Sistemas: es una instalación que se hace una sola vez."],
       ["Muchos productos “Sin foto”", "Puede faltar conexión o la web de Fispa no estar respondiendo. Conviene reintentar más tarde."]],
      [7.0, 10.4])

titulo("Listas futuras y nuevas marcas")
parrafo("Cuando llega una nueva lista de Fispa alcanza con reemplazar lista_proveedor.xlsx y repetir "
        "los pasos 2 a 4. Para incorporar otra marca, el cruce de datos funciona igual siempre que el "
        "proveedor entregue su lista con las mismas columnas. La búsqueda de fotos, en cambio, está "
        "preparada para la web de Fispa y habría que adaptarla.")

doc.save(SALIDA)
print(f"SOP generado: {SALIDA}")
