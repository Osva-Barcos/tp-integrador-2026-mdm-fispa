"""
Generación de Descripcion_Optimizada por REGLAS (Decisión 3).

Estructura obligatoria: [Tipo de pieza] + [Aplicación principal resumida], máximo 90
caracteres, sin repetir la marca "FISPA".

Fuentes:
  - Tipo de pieza: la "Descripcion" del proveedor sin el código de artículo
    (ej. "BOBINA DE IGNICION 70275" -> "BOBINA DE IGNICION"). Es el nombre oficial del
    fabricante, sin abreviaturas. Si el artículo no cruzó, se usa el nombre del ERP completo.
  - Aplicación: el nombre del ERP sin las palabras iniciales que describen el tipo
    (ej. "BULBO TEMP. AUDI A3-A4" -> "AUDI A3-A4"). Si así la descripción queda por
    debajo de 70 caracteres y la "Aplicacion" del proveedor es más completa, se usa esa.
  - Se quitan las palabras con forma de código OEM (6 o más dígitos seguidos, ej.
    "GM90411546"): esos códigos ya están en la columna Cruces_OEM.
  - Cilindradas con punto ("1 6" -> "1.6") y abreviaturas separadas de la palabra siguiente
    ("INYECT.RENAULT" -> "INYECT. RENAULT"), venga el texto de Fispa o del ERP.
  - El resultado se pasa a MAYÚSCULAS para que todas las descripciones sean uniformes.

Todo es determinista: la misma entrada siempre produce la misma descripción.
"""
import re

import config
from transformar import limpiar_texto

# Palabras que pueden aparecer dentro del "tipo de pieza" sin ser aplicación.
CONECTORES = {"DE", "DEL", "PARA", "Y", "CON", "C/", "P/", "LA", "EL", "LOS", "LAS", "-"}

# Abreviaturas habituales del ERP que forman parte del tipo de pieza (no de la aplicación).
ABREVIATURAS_TIPO = {"JGO", "JUEGO", "KITS", "KIT", "ELECTRO", "ENC", "PREC", "INY", "INYECT",
                     "REG", "TEMP", "RPM", "ORING", "ORINGS", "O", "RINGS"}

SEPARADORES_FINALES = " -/,.;:(+|&"

# Palabras que anuncian un código; si el código se quita, se quitan con él ("OEM 12498965").
MARCADORES_CODIGO = {"OEM", "ORIG", "ORIGINAL", "REF", "COD", "CODIGO", "NRO"}

# Un código OEM tiene 6 o más dígitos seguidos (GM90411546, 0258003216, 96482570).
# Años ("2003/2008"), cilindradas ("1.6") y motores ("K4M700") no llegan a 6 dígitos seguidos.
PATRON_CODIGO = re.compile(r"\d{6,}")


def _palabra(token):
    """Palabra sin puntuación, en mayúsculas, para comparar."""
    return re.sub(r"[^\wÑÁÉÍÓÚÜ/]", "", token.upper())


def _parecidas(a, b):
    """
    Dos palabras se consideran la misma si una es prefijo de la otra (mínimo 3 letras).
    Cubre plurales y abreviaturas: BOBINA ~ BOBINAS, TEMP ~ TEMPERATURA, INY ~ INYECCION.
    """
    if not a or not b:
        return False
    if a == b:
        return True
    corta, larga = sorted((a, b), key=len)
    return len(corta) >= 3 and larga.startswith(corta)


def _normalizar_numeros(texto):
    """
    La lista del proveedor (y algunos nombres del ERP) escriben las cilindradas sin punto:
    "1 6 16V" en vez de "1.6 16V". Unimos un dígito suelto + espacio + dígito suelto con un
    punto. No se toca un dígito que ya forma parte de un número con punto o coma ("2 1.5" no
    pasa a "2.1.5"; "1,6 8V" no pasa a "1,6.8V").
    """
    return re.sub(r"(?<![\w.,])(\d) (\d)(?![\d.,])", r"\1.\2", texto)


def separar_abreviaturas(texto):
    """
    El ERP pega la abreviatura con la palabra siguiente: "INYECT.RENAULT" -> "INYECT. RENAULT".
    Solo se agrega el espacio; la abreviatura no se expande (sería interpretar).
    Los números no se tocan ("ORIG.72136", "DIESEL.86/92" quedan igual).
    """
    return re.sub(r"(?<=[A-Za-z]{2})\.(?=[A-Za-z])", ". ", texto)


def tipo_de_pieza(descripcion_proveedor, cod_articulo):
    """Descripción del proveedor sin el código de artículo ni aclaraciones entre paréntesis."""
    tipo = limpiar_texto(descripcion_proveedor).upper()
    tipo = re.sub(r"\(.*?\)", " ", tipo)                # "(PRODUCTO ORIGINAL)"
    tipo = re.sub(r"\(.*$", " ", tipo)                  # paréntesis sin cerrar: "(PROD ORIGINAL"
    if cod_articulo:
        tipo = re.sub(r"(?<!\S)" + re.escape(str(cod_articulo).upper()) + r"(?!\S)", " ", tipo)
    return re.sub(r"\s+", " ", tipo).strip(" -")


def quitar_tipo_del_nombre(nombre_erp, palabras_tipo):
    """
    Quita del comienzo del nombre del ERP las palabras que describen el tipo de pieza
    y devuelve lo que queda (la aplicación).
    """
    # "BULBO TEMP.AUDI" -> "BULBO TEMP. AUDI" (separa palabras pegadas por un punto)
    nombre = re.sub(r"\.(?=[A-Za-zÁÉÍÓÚÑ])", ". ", nombre_erp)
    tokens = nombre.split()
    i = 0
    while i < len(tokens):
        p = _palabra(tokens[i])
        es_tipo = (p in CONECTORES or p in ABREVIATURAS_TIPO or p == ""
                   or any(_parecidas(p, t) for t in palabras_tipo))
        if not es_tipo:
            break
        i += 1
    return " ".join(tokens[i:]).strip(" -./")


def recortar(texto, maximo):
    """Corta en el último espacio antes del máximo y limpia separadores colgantes."""
    if len(texto) <= maximo:
        return texto.strip(SEPARADORES_FINALES)
    corte = texto[:maximo + 1]
    if " " in corte:
        corte = corte[:corte.rfind(" ")]
    else:
        corte = corte[:maximo]
    corte = corte.rstrip(SEPARADORES_FINALES)
    # Si quedó un paréntesis abierto sin cerrar, lo sacamos.
    if corte.count("(") > corte.count(")"):
        corte = corte[:corte.rfind("(")].rstrip(SEPARADORES_FINALES)
    return corte


def quitar_marca(texto):
    """
    Elimina la palabra FISPA (Directiva: no repetir la marca) y los "?" que quedaron
    de caracteres mal codificados en el origen (ej. "Mondeo II ? III" -> "Mondeo II - III").
    También separa palabras pegadas a "O'RINGS" ("O'RINGSMULTIPUNTO" -> "O'RINGS MULTIPUNTO").
    """
    texto = re.sub(r"\s\?\s", " - ", texto).replace("?", " ")
    # (?!S) evita partir un "O'RINGS" ya separado en "O'RING S" si se aplica dos veces.
    texto = re.sub(r"(O'RINGS|O'RING(?!S))(?=[A-Za-z])", r"\1 ", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b" + config.MARCA_A_OMITIR + r"\b", " ", texto, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", texto).strip(" -")


def quitar_codigos(texto):
    """
    Quita las partes de cada palabra que tienen forma de código OEM (6+ dígitos seguidos).
    Las palabras se separan por "-", "/" o "," para no perder modelos pegados a un código:
    "ASTRA-GM90411546" -> "ASTRA". Si se quita un código, también se quita la palabra que
    lo anunciaba justo antes ("OEM 12498965" -> "").
    """
    salida = []
    for token in texto.split():
        partes = re.split(r"([-/,])", token)
        if not any(PATRON_CODIGO.search(p) for p in partes):
            salida.append(token)
            continue
        quedan = "".join(p for p in partes if not PATRON_CODIGO.search(p))
        quedan = re.sub(r"([-/,])[-/,]+", r"\1", quedan).strip("-/,")
        if salida and _palabra(salida[-1]) in MARCADORES_CODIGO:
            salida.pop()
        if quedan:
            salida.append(quedan)
    # Si al quitar un código quedaron dos separadores seguidos ("- 24579418 / TB10046"
    # -> "- / TB10046"), se deja solo el primero.
    limpia = []
    for token in salida:
        if re.fullmatch(r"[-/,|&]+", token) and limpia and re.fullmatch(r"[-/,|&]+", limpia[-1]):
            continue
        limpia.append(token)
    return " ".join(limpia)


def generar_descripcion(nombre_erp, categoria, descripcion_proveedor=None, cod_articulo=None,
                        aplicacion_proveedor=None):
    """Arma la Descripcion_Optimizada de un artículo."""
    nombre = separar_abreviaturas(_normalizar_numeros(
        quitar_codigos(quitar_marca(limpiar_texto(nombre_erp)))))
    tipo = tipo_de_pieza(descripcion_proveedor, cod_articulo) if descripcion_proveedor else ""

    if not tipo:
        # Artículo no cruzado: el nombre del ERP ya tiene la forma [tipo] + [aplicación].
        return recortar(nombre.upper(), config.DESCRIPCION_MAX)

    palabras_tipo = {_palabra(t) for t in (tipo + " " + limpiar_texto(categoria)).split()}
    aplicacion_erp = quitar_tipo_del_nombre(nombre, palabras_tipo)
    aplicacion_prov = quitar_tipo_del_nombre(
        quitar_codigos(_normalizar_numeros(quitar_marca(limpiar_texto(aplicacion_proveedor)))),
        palabras_tipo)

    # Regla principal: tipo oficial del fabricante + aplicación según el nombre del ERP.
    texto = quitar_marca(f"{tipo} {aplicacion_erp}".strip())

    # Si queda corta (< 70) y la aplicación del proveedor es más completa, se usa esa:
    # aprovecha los caracteres disponibles con datos reales (más modelos/motores),
    # lo que mejora la búsqueda en el carrito y en e-commerce.
    if len(texto) < config.DESCRIPCION_MIN and len(aplicacion_prov) > len(aplicacion_erp):
        texto = quitar_marca(f"{tipo} {aplicacion_prov}".strip())

    # Todo en mayúsculas: la mitad de los nombres del ERP mezcla "FORD Courier 1.8 D Endura".
    return recortar(texto.upper(), config.DESCRIPCION_MAX)
