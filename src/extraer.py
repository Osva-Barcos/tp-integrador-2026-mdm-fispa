"""
ETAPA 1 - EXTRACCIÓN

Lee los tres Excel de la carpeta "entrada" y valida que tengan las columnas mínimas.
No transforma datos de negocio: solo los carga como texto para no perder formatos
(por ejemplo, códigos con ceros a la izquierda o con letras).
"""
import logging
import re

import pandas as pd

import config

log = logging.getLogger(__name__)


class ErrorDeEntrada(Exception):
    """Error que se le muestra al usuario tal cual: debe ser claro y sin jerga."""


def _verificar_archivo(ruta):
    if not ruta.exists():
        raise ErrorDeEntrada(
            f"No se encontró el archivo '{ruta.name}' en la carpeta '{ruta.parent}'.\n"
            f"Revise que el archivo esté guardado con ese nombre exacto.")


def _verificar_columnas(df, columnas, nombre_archivo):
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        raise ErrorDeEntrada(
            f"Al archivo '{nombre_archivo}' le faltan estas columnas: {', '.join(faltantes)}.\n"
            f"Columnas encontradas: {', '.join(map(str, df.columns))}")


def _limpiar_nombres_columnas(df):
    # Quita espacios sobrantes en los encabezados ("Precio " -> "Precio").
    df.columns = [str(c).strip() for c in df.columns]
    return df


def convertir_precio(valor):
    """
    Convierte un precio a número (float). Acepta:
      - números ya convertidos por Excel: 1925.86
      - formato argentino como texto:    "-$ 102.733,76-", "$ 1.925,86"
    Devuelve None si el precio está vacío o no se puede interpretar ("-$ - -").
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    # Si es un número "puro" (ej. "1925.86" o "1.5E3"), lo convertimos directo.
    try:
        return float(texto)
    except ValueError:
        pass
    # Formato argentino: sacamos todo lo que no sea dígito, punto o coma.
    texto = re.sub(r"[^\d.,]", "", texto)
    if not re.search(r"\d", texto):
        return None
    texto = texto.replace(".", "").replace(",", ".")  # 102.733,76 -> 102733.76
    try:
        return float(texto)
    except ValueError:
        return None


def leer_erp1():
    """Reporte de Ventas: Código, Nombre y Precio mayorista."""
    _verificar_archivo(config.ARCHIVO_ERP1)
    df = pd.read_excel(config.ARCHIVO_ERP1, dtype=str)
    df = _limpiar_nombres_columnas(df)
    _verificar_columnas(df, config.COLUMNAS_ERP1, config.ARCHIVO_ERP1.name)
    df["Precio_num"] = df["Precio"].map(convertir_precio)
    log.info("ERP1 (ventas): %d filas leídas", len(df))
    return df


def leer_erp2():
    """Reporte de Compras: Código, Marca, Categoría y Código Proveedor."""
    _verificar_archivo(config.ARCHIVO_ERP2)
    df = pd.read_excel(config.ARCHIVO_ERP2, dtype=str)
    df = _limpiar_nombres_columnas(df)
    _verificar_columnas(df, config.COLUMNAS_ERP2, config.ARCHIVO_ERP2.name)
    log.info("ERP2 (compras): %d filas leídas", len(df))
    return df


def leer_lista_proveedor():
    """
    Lista de precios de Fispa. El encabezado real NO está en la primera fila
    (arriba hay un título y la fecha de la lista), así que lo buscamos: es la
    primera fila que contiene la celda "Cod.Articulo".
    """
    _verificar_archivo(config.ARCHIVO_PROVEEDOR)
    crudo = pd.read_excel(config.ARCHIVO_PROVEEDOR, header=None, dtype=str)
    fila_encabezado = None
    for i, fila in crudo.iterrows():
        if any(str(v).strip() == "Cod.Articulo" for v in fila.values):
            fila_encabezado = i
            break
    if fila_encabezado is None:
        raise ErrorDeEntrada(
            f"No se encontró la fila de encabezados (con 'Cod.Articulo') en "
            f"'{config.ARCHIVO_PROVEEDOR.name}'.")

    # Volvemos a leer usando esa fila como encabezado. Pandas renombra solo las
    # columnas repetidas (la segunda "Linea.Descripcion" pasa a "Linea.Descripcion.1").
    df = pd.read_excel(config.ARCHIVO_PROVEEDOR, header=fila_encabezado, dtype=str)
    df = _limpiar_nombres_columnas(df)
    _verificar_columnas(df, config.COLUMNAS_PROVEEDOR, config.ARCHIVO_PROVEEDOR.name)
    # Descartamos filas totalmente vacías (por ejemplo, al final de la planilla).
    df = df.dropna(subset=["Cod.Articulo"])
    df["Importe_num"] = df["Importe"].map(convertir_precio)
    log.info("Lista proveedor: encabezado en fila %d, %d artículos leídos",
             fila_encabezado + 1, len(df))
    return df
