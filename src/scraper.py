"""
Enriquecimiento multimedia: URL de la foto oficial de cada producto en fispaargentina.com.ar.

Cómo arma el sitio sus páginas (relevado a mano antes de programar):
  - Cada rubro tiene UNA página con todos sus productos, sin paginación:
        catalogo.php?productos=<CodRubro>      (CodRubro = "Cod.Rubro" de la lista de Fispa)
  - Cada producto aparece como <div class="producto" id="<Cod.Articulo>"> y, en el mismo
    bloque, su imagen <img src="productos/c/<Cod.Articulo>.jpg?v=...">.
  - Si el producto no tiene foto, el sitio muestra "imagenes/Fispa_imagen.jpg" (genérica).
  - Ficha individual (respaldo): POST kam/m/_busProductos.php con idProd=<Cod.Articulo>.

Por eso recorremos ~85 páginas de rubro en lugar de ~2.000 fichas individuales, y solo
pedimos la ficha de los productos que no aparecieron en ningún rubro.

Buenas prácticas: pausa entre pedidos, reintentos, User-Agent identificado y cache local
(una página ya descargada no se vuelve a pedir).
"""
import hashlib
import logging
import re
import time
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

import config

log = logging.getLogger(__name__)


class ClienteFispa:
    def __init__(self, usar_red=True):
        self.usar_red = usar_red          # False = solo cache (modo sin conexión)
        self.sesion = requests.Session()
        self.sesion.headers["User-Agent"] = config.USER_AGENT
        self.pedidos_realizados = 0
        config.CARPETA_CACHE.mkdir(parents=True, exist_ok=True)

    def _ruta_cache(self, url, datos):
        clave = url + ("|" + repr(sorted(datos.items())) if datos else "")
        return config.CARPETA_CACHE / (hashlib.sha1(clave.encode("utf-8")).hexdigest() + ".html")

    def obtener(self, url, datos=None):
        """Devuelve el HTML de la URL (GET, o POST si hay datos). Usa cache si existe."""
        ruta = self._ruta_cache(url, datos)
        if ruta.exists():
            return ruta.read_text(encoding="utf-8")
        if not self.usar_red:
            return None

        for intento in range(1, config.REINTENTOS + 1):
            time.sleep(config.PAUSA_ENTRE_PEDIDOS)   # respetar el servidor
            try:
                if datos:
                    resp = self.sesion.post(url, data=datos, timeout=config.TIMEOUT_PEDIDO)
                else:
                    resp = self.sesion.get(url, timeout=config.TIMEOUT_PEDIDO)
                self.pedidos_realizados += 1
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or "utf-8"
                ruta.write_text(resp.text, encoding="utf-8")
                return resp.text
            except requests.RequestException as error:
                log.warning("Error al pedir %s (intento %d/%d): %s",
                            url, intento, config.REINTENTOS, error)
        return None


def _url_limpia(src, base):
    """URL absoluta de la imagen, sin el parámetro "?v=..." (es solo para refrescar caches)."""
    absoluta = urljoin(base, src)
    partes = urlsplit(absoluta)
    return urlunsplit((partes.scheme, partes.netloc, partes.path, "", ""))


def _es_placeholder(src):
    return config.IMAGEN_PLACEHOLDER.lower() in (src or "").lower()


def _clave(codigo):
    return str(codigo).strip().upper()


def ids_de_rubros(cliente):
    """Números de rubro publicados en el menú de la página principal."""
    html = cliente.obtener(config.SITIO_FISPA)
    if not html:
        return set()
    return set(re.findall(r"catalogo\.php\?productos=(\d+)", html))


def parsear_rubro(html, base):
    """
    Devuelve {codigo: url_foto_o_None} con todos los productos de una página de rubro.
    None significa que el sitio muestra la imagen genérica (sin foto propia).
    """
    sopa = BeautifulSoup(html, "html.parser")
    resultado = {}
    for div in sopa.select("div.producto[id]"):
        bloque = div.parent                      # el bloque del producto contiene la imagen
        img = bloque.find("img") if bloque else None
        src = img.get("src") if img else None
        resultado[_clave(div["id"])] = None if (not src or _es_placeholder(src)) \
            else _url_limpia(src, base)
    return resultado


def ficha_existe(html):
    """
    Si el código no existe, el sitio igual responde una ficha, pero vacía:
    título "FISPA " sin código y sin nombre de producto.
    """
    sopa = BeautifulSoup(html, "html.parser")
    nombre = sopa.select_one(".prodInfos h2")
    return bool(nombre and nombre.get_text(strip=True))


def parsear_ficha(html, base):
    """Primera imagen de la ficha individual del producto (o None si no tiene)."""
    sopa = BeautifulSoup(html, "html.parser")
    img = sopa.select_one(".prodImgs img") or sopa.find("img")
    src = img.get("src") if img else None
    return None if (not src or _es_placeholder(src)) else _url_limpia(src, base)


def buscar_fotos(codigos, rubros_lista, usar_red=True):
    """
    codigos:      códigos de artículo Fispa (Cod.Articulo) de los productos cruzados.
    rubros_lista: Cod.Rubro presentes en la lista del proveedor (se suman a los del menú).
    Devuelve (fotos, sin_foto): fotos = {codigo: url}; sin_foto = {codigo: motivo}.
    """
    cliente = ClienteFispa(usar_red=usar_red)
    rubros = ids_de_rubros(cliente) | {str(r).strip() for r in rubros_lista if str(r).strip()}
    log.info("Fotos: recorriendo %d páginas de rubro del sitio de Fispa...", len(rubros))

    catalogo_web = {}
    for numero in sorted(rubros, key=lambda x: int(x) if x.isdigit() else 0):
        url = urljoin(config.SITIO_FISPA, f"catalogo.php?productos={numero}")
        html = cliente.obtener(url)
        if html:
            for codigo, foto in parsear_rubro(html, url).items():
                # Si un producto aparece en varios rubros, nos quedamos con la primera foto real.
                if catalogo_web.get(codigo) is None:
                    catalogo_web[codigo] = foto

    fotos, sin_foto = {}, {}
    pendientes = [c for c in codigos if _clave(c) not in catalogo_web]
    if pendientes:
        log.info("Fotos: %d productos no aparecen en los rubros; se consulta su ficha individual",
                 len(pendientes))
    url_ficha = urljoin(config.SITIO_FISPA, "kam/m/_busProductos.php")
    for codigo in pendientes:
        html = cliente.obtener(url_ficha, {"idProd": codigo})
        if html is None:
            sin_foto[codigo] = ("No se pudo consultar el sitio (sin conexión o sin datos en cache)")
        elif ficha_existe(html):
            catalogo_web[_clave(codigo)] = parsear_ficha(html, url_ficha)
        else:
            sin_foto[codigo] = "El producto no se encontró en el sitio de Fispa"

    for codigo in codigos:
        if codigo in sin_foto:
            continue
        foto = catalogo_web.get(_clave(codigo))
        if foto:
            fotos[codigo] = foto
        else:
            sin_foto[codigo] = "El sitio de Fispa muestra la imagen genérica (sin foto propia)"

    log.info("Fotos: %d con foto, %d sin foto, %d pedidos nuevos al sitio (el resto desde cache)",
             len(fotos), len(sin_foto), cliente.pedidos_realizados)
    return fotos, sin_foto
