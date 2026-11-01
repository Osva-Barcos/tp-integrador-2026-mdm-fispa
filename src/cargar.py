"""
ETAPA 3 - CARGA

Escribe los resultados en la carpeta "salida":
  - base_maestra.csv      (UTF-8 con BOM, separado por comas: Excel lo abre con acentos correctos)
  - base_maestra.sqlite   (tablas base_maestra y errores_sin_mapeo)
  - errores_sin_mapeo.csv (log de excepciones)
"""
import logging
import sqlite3

import config

log = logging.getLogger(__name__)


def _escribir_csv(df, ruta):
    try:
        df.to_csv(ruta, index=False, encoding="utf-8-sig")
    except PermissionError:
        raise PermissionError(
            f"No se pudo guardar '{ruta.name}': probablemente está abierto en Excel. "
            f"Ciérrelo y vuelva a ejecutar.") from None


def guardar(base, errores):
    config.CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)

    _escribir_csv(base[config.COLUMNAS_SALIDA], config.ARCHIVO_BASE_CSV)
    _escribir_csv(errores, config.ARCHIVO_ERRORES)

    # SQLite: se recrea completo en cada ejecución.
    if config.ARCHIVO_BASE_SQLITE.exists():
        config.ARCHIVO_BASE_SQLITE.unlink()
    with sqlite3.connect(config.ARCHIVO_BASE_SQLITE) as conexion:
        base[config.COLUMNAS_SALIDA].to_sql("base_maestra", conexion, index=False)
        errores.to_sql("errores_sin_mapeo", conexion, index=False)
        conexion.execute("CREATE UNIQUE INDEX ix_codigo ON base_maestra (Codigo_Interno)")

    log.info("Guardado: %s (%d filas)", config.ARCHIVO_BASE_CSV.name, len(base))
    log.info("Guardado: %s (%d filas)", config.ARCHIVO_ERRORES.name, len(errores))
    log.info("Guardado: %s", config.ARCHIVO_BASE_SQLITE.name)
