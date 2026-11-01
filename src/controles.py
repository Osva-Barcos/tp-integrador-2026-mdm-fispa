"""
CONTROLES DE CALIDAD

Verifica automáticamente la salida antes de distribuirla y genera control_calidad.txt,
escrito para que lo lea el personal administrativo (sin términos técnicos).
"""
import logging

import pandas as pd

import config

log = logging.getLogger(__name__)


def _iguales(a, b):
    """Compara dos columnas celda por celda, considerando iguales dos celdas vacías."""
    a = a.reset_index(drop=True)
    b = b.reset_index(drop=True)
    return bool(((a == b) | (a.isna() & b.isna())).all())


def ejecutar_controles(base, errores, erp1, erp2, sin_foto):
    """Devuelve (lineas_resumen, hay_errores_graves)."""
    total = len(base)
    cruzados = int(base["_cruzado"].sum())
    graves = []
    lineas = []

    def ok(condicion, texto_ok, texto_error, grave=True):
        if condicion:
            lineas.append(f"[OK]     {texto_ok}")
        else:
            lineas.append(f"[REVISAR] {texto_error}")
            if grave:
                graves.append(texto_error)

    # 1. Cantidades
    ok(total == len(erp2), f"Artículos en la base maestra: {total} (igual al maestro de compras)",
       f"La base tiene {total} artículos pero compras tiene {len(erp2)}")
    ok(cruzados + len(errores) == total,
       f"Cruzados con Fispa ({cruzados}) + excepciones ({len(errores)}) = {total}",
       f"Cruzados ({cruzados}) + excepciones ({len(errores)}) no suman {total}")

    # 2. Inmutabilidad: Código, Marca y Categoría idénticos al ERP
    erp2_ordenado = erp2.set_index("Código").loc[base["Codigo_Interno"]].reset_index()
    ok(_iguales(base["Codigo_Interno"], erp2_ordenado["Código"])
       and _iguales(base["Marca"], erp2_ordenado["Marca"])
       and _iguales(base["Categoria"], erp2_ordenado["Categoría"]),
       "Código interno, Marca y Categoría idénticos al ERP (sin modificaciones)",
       "Código interno, Marca o Categoría NO coinciden con el ERP")
    ok(set(base["Codigo_Interno"]) <= set(erp1["Código"]),
       "Todos los códigos internos existen en el reporte de ventas",
       "Hay códigos de la base que no están en el reporte de ventas", grave=False)

    # 3. Descripción optimizada
    largos = base["Descripcion_Optimizada"].str.len()
    ok((largos > config.DESCRIPCION_MAX).sum() == 0,
       f"Descripciones de hasta {config.DESCRIPCION_MAX} caracteres "
       f"(mín {largos.min()}, promedio {largos.mean():.0f}, máx {largos.max()})",
       f"{(largos > config.DESCRIPCION_MAX).sum()} descripciones superan {config.DESCRIPCION_MAX} caracteres")
    con_marca = base["Descripcion_Optimizada"].str.contains(config.MARCA_A_OMITIR, case=False).sum()
    ok(con_marca == 0, f"Ninguna descripción repite la palabra {config.MARCA_A_OMITIR}",
       f"{con_marca} descripciones contienen la palabra {config.MARCA_A_OMITIR}")
    ok((largos == 0).sum() == 0, "Ningún artículo quedó sin descripción",
       f"{(largos == 0).sum()} artículos sin descripción")
    en_rango = int(((largos >= config.DESCRIPCION_MIN) & (largos <= config.DESCRIPCION_MAX)).sum())
    lineas.append(f"[INFO]   Descripciones entre {config.DESCRIPCION_MIN} y {config.DESCRIPCION_MAX} "
                  f"caracteres: {en_rango}; más cortas: {total - en_rango} "
                  f"(el nombre de origen no tiene más información)")

    # 4. Precios
    precio_cero = base[base["Precio"].fillna(0) == 0]
    ok(len(precio_cero) == 0, "No hay precios en cero ni vacíos",
       f"{len(precio_cero)} artículos con precio en CERO o vacío (ver lista abajo)", grave=False)
    costo_vacio_cruzado = base[base["_cruzado"] & base["Costo_Reposicion"].isna()]
    ok(len(costo_vacio_cruzado) == 0, "Todos los artículos cruzados tienen costo de reposición",
       f"{len(costo_vacio_cruzado)} artículos cruzados sin costo de reposición", grave=False)

    # 5. Fotos y EAN
    con_foto = int((base["URL_Foto"].fillna("") != "").sum())
    lineas.append(f"[INFO]   Artículos con foto: {con_foto}; cruzados sin foto en el sitio: "
                  f"{len(sin_foto)} (detalle en log_proceso.txt)")
    con_ean = int((base["EAN13"].fillna("") != "").sum())
    lineas.append(f"[INFO]   EAN-13 válidos encontrados: {con_ean} "
                  f"(la lista de Fispa no trae códigos EAN-13 válidos)")

    # 6. Excepciones por motivo
    for motivo, cantidad in errores["Motivo"].value_counts().items():
        lineas.append(f"[INFO]   Excepciones '{motivo}': {cantidad}")

    # Archivo para el usuario
    with open(config.ARCHIVO_CONTROL, "w", encoding="utf-8-sig") as f:
        f.write("CONTROL DE CALIDAD - BASE MAESTRA FISPA\n")
        f.write(f"Fecha: {pd.Timestamp.now():%d/%m/%Y %H:%M}\n\n")
        f.write("\n".join(lineas) + "\n")
        if len(precio_cero):
            f.write("\nARTÍCULOS CON PRECIO EN CERO O VACÍO (corregir en el ERP antes de publicar):\n")
            for _, fila in precio_cero.iterrows():
                f.write(f"  - {fila['Codigo_Interno']}: {fila['Descripcion_Optimizada']}\n")
        f.write("\nRESULTADO: " + ("HAY PROBLEMAS GRAVES, NO DISTRIBUIR.\n" if graves
                                   else "Sin errores graves. Revisar los puntos [REVISAR] y "
                                        "el archivo errores_sin_mapeo.csv antes de distribuir.\n"))
    return lineas, bool(graves)
