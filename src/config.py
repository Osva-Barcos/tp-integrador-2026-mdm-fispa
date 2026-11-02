"""
Configuración central del pipeline.

Acá están TODOS los parámetros que un usuario podría querer cambiar sin tocar la lógica:
rutas de carpetas, nombres de archivos, columnas esperadas y tiempos del scraper.
"""
from pathlib import Path

# --- Carpetas -----------------------------------------------------------------
# La raíz del proyecto es la carpeta que contiene a "src".
RAIZ = Path(__file__).resolve().parent.parent
CARPETA_ENTRADA = RAIZ / "entrada"   # donde el administrativo deja los 3 Excel
CARPETA_SALIDA = RAIZ / "salida"     # donde quedan los resultados
CARPETA_CACHE = RAIZ / "cache"       # páginas web ya descargadas (para no repetir pedidos)

# --- Archivos de entrada (nombres exactos que exige el SOP) ---------------------
ARCHIVO_ERP1 = CARPETA_ENTRADA / "erp1_ventas.xlsx"
ARCHIVO_ERP2 = CARPETA_ENTRADA / "erp2_compras.xlsx"
ARCHIVO_PROVEEDOR = CARPETA_ENTRADA / "lista_proveedor.xlsx"

# --- Archivos de salida ---------------------------------------------------------
ARCHIVO_BASE_CSV = CARPETA_SALIDA / "base_maestra.csv"
ARCHIVO_BASE_SQLITE = CARPETA_SALIDA / "base_maestra.sqlite"
ARCHIVO_ERRORES = CARPETA_SALIDA / "errores_sin_mapeo.csv"
ARCHIVO_LOG = CARPETA_SALIDA / "log_proceso.txt"
ARCHIVO_CONTROL = CARPETA_SALIDA / "control_calidad.txt"
ARCHIVO_PRECIO_MENOR_COSTO = CARPETA_SALIDA / "precio_menor_costo.csv"

# --- Columnas mínimas que debe traer cada archivo --------------------------------
# Si falta alguna, el pipeline se detiene con un mensaje claro (no adivina).
COLUMNAS_ERP1 = ["Código", "Producto/Nombre", "Precio"]
COLUMNAS_ERP2 = ["Código", "Marca", "Categoría", "Codigo Proveedor"]
COLUMNAS_PROVEEDOR = ["Cod.Rubro", "Rubro", "Cod.Articulo", "Descripcion", "Importe",
                      "CodigoBarras", "Cod.Ref.Aux", "Aplicacion"]

# Columnas de la lista del proveedor que son copias de otras (Decisión 5).
# El pipeline verifica que sigan siendo idénticas y avisa si alguna vez difieren.
COLUMNAS_DUPLICADAS = [("Cod.Ref.Aux", "Referencia"), ("Aplicacion", "Cod.Linea")]

# --- Esquema de salida (Anexo 2 de la consigna, en este orden exacto) ----------
COLUMNAS_SALIDA = [
    "Codigo_Interno", "Marca", "Categoria", "Codigo_Proveedor", "Descripcion_Optimizada",
    "Precio", "Costo_Reposicion", "EAN13", "Cruces_OEM", "Aplicacion_Completa", "URL_Foto",
]

# --- Descripción optimizada -------------------------------------------------------
DESCRIPCION_MAX = 90   # tope duro de caracteres
DESCRIPCION_MIN = 70   # objetivo mínimo (las más cortas se informan, no se rellenan)
# La marca que no se repite en la descripción se toma de la columna Marca de cada artículo
# (no está fija acá), así el proceso sirve igual para otras marcas.

# --- Scraper de fotos ---------------------------------------------------------------
SITIO_FISPA = "https://fispaargentina.com.ar/"
PAUSA_ENTRE_PEDIDOS = 1.5     # segundos entre pedidos al sitio (respetar el servidor)
TIMEOUT_PEDIDO = 30           # segundos máximos de espera por pedido
REINTENTOS = 3                # reintentos ante errores de red
USER_AGENT = ("Mozilla/5.0 (compatible; PipelineMDM-UTN-FRSF/1.0; "
              "trabajo practico Sistemas de Gestion)")
# Imagen que el sitio muestra cuando el producto NO tiene foto propia.
IMAGEN_PLACEHOLDER = "Fispa_imagen.jpg"
