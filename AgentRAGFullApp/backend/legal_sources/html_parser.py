"""
Parser de HTML de normas legales colombianas → estructura JSON.
Funciona con HTML de Senado y Función Pública.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logger.warning("beautifulsoup4 not installed. HTML parsing will use regex fallback.")


def parse_norm_html(html: str, source: str = "senado") -> dict:
    """
    Parsea HTML de una norma legal y extrae estructura.

    Args:
        html: HTML crudo de la norma
        source: "senado" o "funcion_publica"

    Returns:
        dict con keys: titulo, texto_completo, articulos, metadata
    """
    if HAS_BS4:
        return _parse_with_bs4(html, source)
    else:
        return _parse_with_regex(html, source)


def _parse_with_bs4(html: str, source: str) -> dict:
    """Parseo con BeautifulSoup (preferido)."""
    soup = BeautifulSoup(html, "lxml" if _has_lxml() else "html.parser")

    # Remover scripts, estilos, navegación
    for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    # Extraer título
    titulo = _extract_title_bs4(soup, source)

    # Extraer texto completo
    if source == "senado":
        content_div = soup.find("div", class_="contenidonorma") or soup.find("div", id="TextoNorma") or soup.body
    else:
        content_div = soup.find("div", class_="contenido") or soup.find("div", id="contenido") or soup.body

    texto_completo = content_div.get_text(separator="\n", strip=True) if content_div else soup.get_text(separator="\n", strip=True)

    # Extraer artículos
    articulos = _extract_articles_bs4(soup, texto_completo)

    return {
        "titulo": titulo,
        "texto_completo": texto_completo,
        "articulos": articulos,
        "metadata": {
            "source": source,
            "char_count": len(texto_completo),
            "articulos_count": len(articulos),
        }
    }


def _extract_title_bs4(soup, source: str) -> str:
    """Extrae el título de la norma."""
    # Intentar tag title
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
        if title and len(title) > 5:
            # Limpiar sufijos comunes
            title = re.sub(r'\s*[-|].*$', '', title)
            return title

    # Intentar h1
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)[:200]

    # Intentar primer h2 o h3
    for tag in ["h2", "h3"]:
        header = soup.find(tag)
        if header:
            return header.get_text(strip=True)[:200]

    return "Sin título"


def _extract_articles_bs4(soup, texto_completo: str) -> list[dict]:
    """Extrae artículos individuales del texto."""
    articulos = []

    # Patrón para artículos: "ARTÍCULO 1o.", "Artículo 1.", "ART. 1"
    pattern = r'(?:ART[ÍI]CULO|Art[ií]culo|ART\.?)\s+(\d+[a-zA-Z]?)[º°o.]?\s*[-.]?\s*'

    parts = re.split(f'({pattern})', texto_completo)

    i = 0
    while i < len(parts):
        # Buscar inicio de artículo
        match = re.match(pattern, parts[i]) if i < len(parts) else None
        if match:
            numero = match.group(1) if match.lastindex else ""
            # El contenido es el siguiente fragmento
            contenido = parts[i + 1] if i + 1 < len(parts) else ""

            # Extraer título del artículo (primera línea o frase antes del punto)
            titulo_match = re.match(r'^([^.]{5,100})\.\s', contenido)
            titulo = titulo_match.group(1) if titulo_match else ""

            articulos.append({
                "numero": numero,
                "titulo": titulo[:200],
                "contenido": contenido[:2000],  # Limitar tamaño
            })
        i += 1

    # Fallback: si no se encontraron artículos con el split, usar regex directo
    if not articulos:
        for match in re.finditer(
            r'(?:ART[ÍI]CULO|Art[ií]culo|ART\.?)\s+(\d+[a-zA-Z]?)[º°o.]?\s*[-.]?\s*(.{10,500}?)(?=(?:ART[ÍI]CULO|Art[ií]culo|ART\.?)\s+\d|$)',
            texto_completo,
            re.DOTALL
        ):
            articulos.append({
                "numero": match.group(1),
                "titulo": "",
                "contenido": match.group(2).strip()[:2000],
            })

    return articulos


def _parse_with_regex(html: str, source: str) -> dict:
    """Parseo fallback con regex (sin BeautifulSoup)."""
    # Remover tags HTML básico
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.strip()

    # Título
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    titulo = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else "Sin título"

    return {
        "titulo": titulo[:200],
        "texto_completo": text,
        "articulos": [],
        "metadata": {"source": source, "char_count": len(text), "parser": "regex_fallback"}
    }


def _has_lxml() -> bool:
    try:
        import lxml
        return True
    except ImportError:
        return False
