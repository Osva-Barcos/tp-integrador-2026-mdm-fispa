"""
PIPELINE ETL - BASE MAESTRA NORMALIZADA (GOLDEN RECORD) FISPA

Orquesta las etapas:
  1. Extracción     (extraer.py)     -> lee los 3 Excel de "entrada"
  2. Transformación (transformar.py) -> une ERP1+ERP2 y cruza con la lista de Fispa
                    (descripcion.py) -> genera Descripcion_Optimizada
                    (scraper.py)     -> URL de la foto oficial
  3. Carga          (cargar.py)      -> CSV, SQLite y log de excepciones
  4. Controles      (controles.py)   -> verificaciones de calidad

Uso:
    python src/pipeline.py              (normal: consulta el sitio de Fispa, usando cache)
    python src/pipeline.py --sin-fotos  (sin conexión: solo usa las páginas ya guardadas en cache)
"""
import argparse
import logging
import sys

import pandas as pd

import cargar
import config
import controles
import descripcion
import extraer
import scraper
import transformar

log = logging.getLogger("pipeline")


def configurar_log():
    config.CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    formato = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%d/%m/%Y %H:%M:%S")
    archivo = logging.FileHandler(config.ARCHIVO_LOG, mode="w", encoding="utf-8")
    archivo.setFormatter(formato)
    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(logging.Formatter("  %(message)s"))
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.handlers = [archivo, consola]
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def _vacio_a_none(valor):
    return None if pd.isna(valor) else valor


def construir_base(cruce, fotos):
    """Arma la tabla final con el esquema del Anexo 2."""
    base = pd.DataFrame({
        # Inmutables: se copian tal cual vienen del ERP (sin recortar ni corregir).
        "Codigo_Interno": cruce["Código"],
        "Marca": cruce["Marca"],
        "Categoria": cruce["Categoría"],
        # Código del fabricante limpio (sin espacios sobrantes).
        "Codigo_Proveedor": cruce["Codigo Proveedor"].map(
            lambda v: "" if pd.isna(v) else str(v).strip()),
        "Descripcion_Optimizada": [
            descripcion.generar_descripcion(
                f["Producto/Nombre"], f["Categoría"],
                _vacio_a_none(f["Descripcion"]) if f["cruzado"] else None,
                _vacio_a_none(f["Cod.Articulo"]) if f["cruzado"] else None,
                _vacio_a_none(f["Aplicacion"]) if f["cruzado"] else None)
            for _, f in cruce.iterrows()],
        "Precio": cruce["Precio_num"],
        "Costo_Reposicion": cruce["Importe_num"],
        "EAN13": cruce["CodigoBarras"].map(transformar.obtener_ean13),
        "Cruces_OEM": cruce["Cod.Ref.Aux"].map(transformar.limpiar_oem),
        "Aplicacion_Completa": cruce["Aplicacion"].map(transformar.limpiar_texto),
        "URL_Foto": cruce["Cod.Articulo"].map(lambda c: fotos.get(c, "") if pd.notna(c) else ""),
    })
    base["_cruzado"] = cruce["cruzado"].values   # columna auxiliar para controles (no se exporta)
    return base


def main():
    parser = argparse.ArgumentParser(description="Genera la Base Maestra Normalizada Fispa")
    parser.add_argument("--sin-fotos", action="store_true",
                        help="no consulta el sitio de Fispa; usa solo las páginas en cache")
    args = parser.parse_args()

    configurar_log()
    log.info("=== INICIO DEL PROCESO: BASE MAESTRA FISPA ===")

    # 1. EXTRACCIÓN
    log.info("[1/5] Leyendo archivos de la carpeta 'entrada'...")
    erp1 = extraer.leer_erp1()
    erp2 = extraer.leer_erp2()
    proveedor = extraer.leer_lista_proveedor()

    # 2. TRANSFORMACIÓN
    log.info("[2/5] Uniendo reportes del ERP y cruzando con la lista de Fispa...")
    erp = transformar.unir_erp(erp1, erp2)
    cruce = transformar.cruzar_con_proveedor(erp, proveedor)
    errores = transformar.armar_excepciones(cruce, proveedor)
    for _, e in errores.iterrows():
        log.info("Excepción %s | %s | %s %s", e["Codigo_Interno"], e["Motivo"], e["Detalle"],
                 ("| " + e["Sugerencia_Revision"]) if e["Sugerencia_Revision"] else "")

    # 3. FOTOS
    log.info("[3/5] Buscando fotos en el sitio de Fispa (puede tardar unos minutos la primera vez)...")
    codigos = cruce.loc[cruce["cruzado"], "Cod.Articulo"].unique().tolist()
    try:
        fotos, sin_foto = scraper.buscar_fotos(codigos, proveedor["Cod.Rubro"].dropna().unique(),
                                               usar_red=not args.sin_fotos)
    except Exception as error:  # el resto del proceso no debe frenarse por falta de internet
        log.error("No se pudieron obtener las fotos: %s. La base se genera sin fotos.", error)
        fotos, sin_foto = {}, {c: "Error al consultar el sitio" for c in codigos}
    for codigo, motivo in sorted(sin_foto.items()):
        log.info("Sin foto | Cod.Articulo %s | %s", codigo, motivo)

    # 4. CARGA
    log.info("[4/5] Generando la base maestra y guardando archivos...")
    base = construir_base(cruce, fotos)
    cargar.guardar(base, errores)

    # 5. CONTROLES
    log.info("[5/5] Controles de calidad:")
    lineas, graves = controles.ejecutar_controles(base, errores, erp1, erp2, sin_foto)
    for linea in lineas:
        log.info(linea)
    log.info("=== FIN DEL PROCESO %s ===", "CON ERRORES GRAVES" if graves else "OK")
    return 1 if graves else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.exit(main())
    except (extraer.ErrorDeEntrada, PermissionError) as error:
        logging.getLogger("pipeline").error("PROBLEMA: %s", error)
        sys.exit(2)
