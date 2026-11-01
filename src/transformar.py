"""
ETAPA 2 - TRANSFORMACIÓN

1. Unión interna ERP1 + ERP2 por Código interno.
2. Cruce determinista con la lista del proveedor: ERP[CodigoProveedor] = Proveedor[Cod.Articulo].
3. Clasificación de excepciones (artículos que no se pudieron cruzar) y sugerencias
   para revisión humana (que NUNCA se usan para cruzar).
4. Limpieza de textos y validación de EAN-13.

Reglas inviolables: Código interno, Marca y Categoría se copian tal cual vienen del ERP.
"""
import logging
import re

import pandas as pd

import config

log = logging.getLogger(__name__)

# Motivos de excepción (aparecen en errores_sin_mapeo.csv)
MOTIVO_SIN_CODIGO = "SIN_CODIGO_PROVEEDOR"
MOTIVO_NO_EN_LISTA = "NO_FIGURA_EN_LISTA_FABRICANTE"


# ------------------------------------------------------------------------------
# Utilidades de texto
# ------------------------------------------------------------------------------
def limpiar_texto(valor):
    """
    Limpia un texto "libre" del proveedor:
      - quita caracteres de control (Excel a veces los guarda como "_x001F_")
      - colapsa espacios repetidos y recorta los extremos
    Devuelve "" si el valor está vacío.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)) or pd.isna(valor):
        return ""
    texto = str(valor)
    texto = re.sub(r"_x[0-9A-Fa-f]{4}_", " ", texto)       # caracteres de control escapados
    texto = re.sub(r"[\x00-\x1f\x7f]", " ", texto)          # caracteres de control reales
    texto = reparar_caracteres(texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def reparar_caracteres(texto):
    """
    Repara caracteres que se rompieron en la exportación de la lista de Fispa, solo
    cuando hay evidencia de cuál era el original:
      - "O?RINGS" / "OïRINGS" -> "O'RINGS": la web de Fispa escribe "KIT FILTROS Y O'RINGS".
      - " ? " entre espacios -> " - ": es un separador perdido ("2005 ? 2016", "Cummins ? MWM").
    Los demás "?" se dejan como están ("1? SERIE", "Salida ?8"): adivinar si eran
    "ª", "º" o "Ø" sería inventar datos.
    """
    texto = re.sub(r"\bO[?ïÏ´`’](RINGS?)", r"O'\1", texto, flags=re.IGNORECASE)
    return re.sub(r"(?<=\s)\?(?=\s)", "-", texto)


def normalizar_clave(valor):
    """
    Clave de cruce (Decisión 4): solo se quitan espacios de los extremos y se pasa
    a mayúsculas. NO se quitan guiones ni espacios internos: "FI-028" y "FI 028"
    siguen siendo códigos distintos. Así el cruce sigue siendo 1 a 1 (determinista).
    """
    if valor is None or pd.isna(valor):
        return ""
    return str(valor).strip().upper()


def es_ean13_valido(valor):
    """
    Un EAN-13 válido tiene exactamente 13 dígitos y su último dígito es el
    verificador calculado según el estándar GS1 (pesos 1 y 3 alternados).
    """
    if not re.fullmatch(r"\d{13}", valor or ""):
        return False
    digitos = [int(d) for d in valor]
    suma = sum(d * (3 if i % 2 else 1) for i, d in enumerate(digitos[:12]))
    verificador = (10 - suma % 10) % 10
    return verificador == digitos[12]


# ------------------------------------------------------------------------------
# 1. Unión interna ERP1 + ERP2
# ------------------------------------------------------------------------------
def unir_erp(erp1, erp2):
    """
    ERP2 (compras) define el catálogo activo; ERP1 (ventas) aporta Nombre y Precio.
    Se une por Código interno exacto (sin normalizar: es la clave primaria del ERP).
    """
    for nombre, df in (("ERP1", erp1), ("ERP2", erp2)):
        duplicados = df["Código"][df["Código"].duplicated()].tolist()
        if duplicados:
            raise ValueError(f"{nombre} tiene códigos internos repetidos: {duplicados[:10]}")

    ventas = erp1[["Código", "Producto/Nombre", "Precio_num"]]
    union = erp2.merge(ventas, on="Código", how="outer", indicator=True, validate="one_to_one")

    # "left_only" = solo en ERP2 (compras); "right_only" = solo en ERP1 (ventas)
    solo_erp1 = union.loc[union["_merge"] == "right_only", "Código"]
    solo_erp2 = union.loc[union["_merge"] == "left_only", "Código"]
    if len(solo_erp1):
        log.warning("%d códigos están en ventas pero NO en compras (se excluyen): %s",
                    len(solo_erp1), solo_erp1.tolist()[:20])
    if len(solo_erp2):
        log.warning("%d códigos están en compras pero NO en ventas (quedan sin precio): %s",
                    len(solo_erp2), solo_erp2.tolist()[:20])

    # Nos quedamos con los SKU activos del maestro de compras (ERP2).
    union = union[union["_merge"] != "right_only"].drop(columns="_merge")
    log.info("Unión ERP1 + ERP2: %d artículos activos", len(union))
    return union.reset_index(drop=True)


# ------------------------------------------------------------------------------
# 2. Cruce con la lista del proveedor
# ------------------------------------------------------------------------------
def verificar_columnas_duplicadas(proveedor):
    """Decisión 5: confirma que las columnas 'copia' sigan siendo idénticas."""
    for original, copia in config.COLUMNAS_DUPLICADAS:
        if copia not in proveedor.columns:
            continue
        a = proveedor[original].map(limpiar_texto)
        b = proveedor[copia].map(limpiar_texto)
        distintas = int((a != b).sum())
        if distintas:
            log.warning("Las columnas '%s' y '%s' difieren en %d filas; se usa '%s'.",
                        original, copia, distintas, original)
        else:
            log.info("Columnas '%s' y '%s' son idénticas: se usa '%s'.", original, copia, original)


def cruzar_con_proveedor(erp, proveedor):
    """
    Cruce determinista: clave normalizada de ERP[Codigo Proveedor] == clave de Proveedor[Cod.Articulo].
    Se usa un LEFT JOIN para conservar los 2.184 SKU activos (Decisión 1): los que no cruzan
    quedan con los datos de Fispa vacíos y se informan como excepción.
    """
    verificar_columnas_duplicadas(proveedor)

    prov = proveedor.copy()
    prov["clave"] = prov["Cod.Articulo"].map(normalizar_clave)
    colisiones = prov["clave"][prov["clave"].duplicated()].unique().tolist()
    if colisiones:
        # Si dos artículos del proveedor tienen la misma clave, el cruce dejaría de ser unívoco.
        raise ValueError(f"La lista del proveedor tiene códigos repetidos: {colisiones[:10]}")

    erp = erp.copy()
    erp["clave"] = erp["Codigo Proveedor"].map(normalizar_clave)

    columnas_prov = ["clave", "Cod.Articulo", "Rubro", "Descripcion", "Importe_num",
                     "CodigoBarras", "Cod.Ref.Aux", "Aplicacion"]
    cruce = erp.merge(prov[columnas_prov], on="clave", how="left", validate="many_to_one")
    cruce["cruzado"] = cruce["Cod.Articulo"].notna() & (cruce["clave"] != "")

    # Aviso (Decisión 6): varios SKU internos que apuntan al mismo código de proveedor.
    compartidos = cruce[cruce["cruzado"]].groupby("clave")["Código"].apply(list)
    compartidos = compartidos[compartidos.map(len) > 1]
    for clave, codigos in compartidos.items():
        log.warning("Código de proveedor '%s' compartido por varios SKU: %s "
                    "(se enriquecen todos; revisar con Compras)", clave, ", ".join(codigos))

    log.info("Cruce con lista del proveedor: %d cruzados, %d sin cruzar",
             int(cruce["cruzado"].sum()), int((~cruce["cruzado"]).sum()))
    return cruce


# ------------------------------------------------------------------------------
# 3. Excepciones y sugerencias de revisión
# ------------------------------------------------------------------------------
def _sugerir(clave, claves_proveedor, sin_separadores):
    """
    Busca códigos PARECIDOS en la lista del proveedor, solo para ayudar a la persona
    que revisa el log (Decisión 7). Estas sugerencias NO se usan para cruzar.
    Criterios: igual ignorando espacios/guiones, o diferencia de una letra final.
    """
    candidatos = []
    compacta = re.sub(r"[\s\-_./]", "", clave)
    candidatos += sin_separadores.get(compacta, [])
    for letra in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":           # 285600 -> 285600A
        if clave + letra in claves_proveedor:
            candidatos.append(clave + letra)
    if re.search(r"\d[A-Z]$", clave) and clave[:-1] in claves_proveedor:  # 22749A -> 22749
        candidatos.append(clave[:-1])
    candidatos = [c for c in dict.fromkeys(candidatos) if c != clave]
    if not candidatos:
        return ""
    return "Posible equivalente en lista: " + ", ".join(candidatos) + " (verificar manualmente)"


def armar_excepciones(cruce, proveedor):
    claves_proveedor = set(proveedor["Cod.Articulo"].map(normalizar_clave))
    sin_separadores = {}
    for c in claves_proveedor:
        sin_separadores.setdefault(re.sub(r"[\s\-_./]", "", c), []).append(c)

    filas = []
    for _, fila in cruce[~cruce["cruzado"]].iterrows():
        if fila["clave"] == "":
            motivo, detalle, sugerencia = (MOTIVO_SIN_CODIGO,
                                           "El artículo no tiene Código Proveedor cargado en el ERP",
                                           "")
        else:
            motivo = MOTIVO_NO_EN_LISTA
            detalle = f"El código '{fila['Codigo Proveedor']}' no figura en la lista de Fispa"
            sugerencia = _sugerir(fila["clave"], claves_proveedor, sin_separadores)
        filas.append({
            "Codigo_Interno": fila["Código"],
            "Marca": fila["Marca"],
            "Categoria": fila["Categoría"],
            "Codigo_Proveedor": "" if pd.isna(fila["Codigo Proveedor"]) else fila["Codigo Proveedor"],
            "Nombre_ERP": fila["Producto/Nombre"],
            "Motivo": motivo,
            "Detalle": detalle,
            "Sugerencia_Revision": sugerencia,
        })
    return pd.DataFrame(filas, columns=["Codigo_Interno", "Marca", "Categoria", "Codigo_Proveedor",
                                        "Nombre_ERP", "Motivo", "Detalle", "Sugerencia_Revision"])


# ------------------------------------------------------------------------------
# 4. Cruces OEM
# ------------------------------------------------------------------------------
def limpiar_oem(valor):
    """
    Decisión 10: ordena las equivalencias originales sin perder información.
      - quita el prefijo "REF ORIG" y sus variantes (REF.ORIG., REF ORG, REF OEM...),
        que se repite en el 80% de las filas y no aporta a la búsqueda;
      - unifica los separadores " - " existentes como " | ";
      - si el valor era solo guiones ("----------"), queda vacío.
    NO se parte por espacios: hay códigos con espacios internos ("D51 84") y marcas
    delante de sus códigos ("FIAT 7735919"); separarlos sería adivinar.
    """
    texto = limpiar_texto(valor)
    # Variantes vistas en la lista: REF ORIG, REF.ORIG., REF. ORIG, REF ORIGINAL, REF ORIGI,
    # REF ORI, REF ORlG (L por error de tipeo), REF ORG, REF OEM; a veces seguidas de ":".
    # (?![A-Za-z0-9]) obliga a cortar en palabra completa (evita dejar restos como "INAL"
    # o "I"); el "_" de "REF.ORIG_" se descarta junto con los espacios, puntos y ":".
    texto = re.sub(r"^REF\W*(ORIGINAL|ORIGI|ORIG|ORLG|ORI|ORG|OEM)(?![A-Za-z0-9])[\s.:_]*", "",
                   texto,
                   flags=re.IGNORECASE)
    texto = re.sub(r"\s+-\s+", " | ", texto)
    return texto.strip(" -|")


# ------------------------------------------------------------------------------
# 5. EAN-13
# ------------------------------------------------------------------------------
def obtener_ean13(valor):
    """
    Decisión 2: solo se carga el código de barras si es un EAN-13 válido.
    En la lista actual ningún valor lo es (son copias del código de artículo),
    por eso la columna queda vacía en lugar de llenarse con datos falsos.
    """
    texto = limpiar_texto(valor)
    return texto if es_ean13_valido(texto) else ""
