"""
Cliente para la API de datos.gov.co (Socrata SODA API).
Accede a:
  - SUIN-Juriscol: 87,000+ normas (dataset fiev-nid6)
  - Corte Constitucional: sentencias (dataset v2k4-2t8s)

API pública, sin autenticación requerida.
"""
import logging
from typing import Optional
import httpx

from .base_source import BaseLegalSource
from derogation.models import LiveSourceResult

logger = logging.getLogger(__name__)

# Dataset IDs en datos.gov.co
SUIN_JURISCOL_DATASET = "fiev-nid6"
CORTE_CC_DATASET = "v2k4-2t8s"
BASE_API_URL = "https://www.datos.gov.co/resource"

# Timeout para requests
TIMEOUT = httpx.Timeout(15.0, connect=10.0)


class DatosGovCoSource(BaseLegalSource):
    """
    Fuente legal: datos.gov.co (Socrata SODA API).
    Acceso a SUIN-Juriscol (normas) y Corte Constitucional (sentencias).
    """

    name = "datos_gov"
    description = "Datos Abiertos Colombia - SUIN-Juriscol + Corte Constitucional"
    base_url = "https://www.datos.gov.co"
    is_api = True

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=TIMEOUT)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # --- SUIN-Juriscol: Normas ---

    async def search(self, query: str, limit: int = 10, **kwargs) -> list[LiveSourceResult]:
        """Busca normas en SUIN-Juriscol via Socrata API."""
        tipo_filter = kwargs.get("tipo")
        anio_filter = kwargs.get("anio")

        params = {
            "$q": query,
            "$limit": str(limit),
        }

        # Build WHERE clause
        where_parts = []
        if tipo_filter:
            where_parts.append(f"tipo='{tipo_filter.upper()}'")
        if anio_filter:
            where_parts.append(f"ano='{anio_filter}'")
        if where_parts:
            params["$where"] = " AND ".join(where_parts)

        try:
            client = await self._get_client()
            url = f"{BASE_API_URL}/{SUIN_JURISCOL_DATASET}.json"
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data:
                results.append(LiveSourceResult(
                    source="datos_gov_suin",
                    tipo=item.get("tipo", ""),
                    numero=int(item["numero"]) if item.get("numero", "").isdigit() else None,
                    anio=int(item["ano"]) if item.get("ano", "").isdigit() else None,
                    titulo=item.get("subtipo", ""),
                    estado=item.get("vigencia", ""),
                    url=None,
                    preview=f"{item.get('tipo', '')} {item.get('numero', '')} de {item.get('ano', '')} - {item.get('subtipo', '')}",
                    metadata={
                        "sector": item.get("sector", ""),
                        "entidad": item.get("entidad", ""),
                        "materia": item.get("materia", ""),
                        "vigencia": item.get("vigencia", ""),
                    }
                ))

            logger.info(f"datos.gov.co SUIN: {len(results)} normas encontradas para '{query}'")
            return results

        except httpx.HTTPError as e:
            logger.error(f"Error consultando datos.gov.co SUIN: {e}")
            return []

    async def search_norma(self, tipo: str, numero: int, anio: int) -> list[dict]:
        """Busca una norma específica por tipo, número y año."""
        params = {
            "$where": f"tipo='{tipo.upper()}' AND numero='{numero}' AND ano='{anio}'",
            "$limit": "5",
        }

        try:
            client = await self._get_client()
            url = f"{BASE_API_URL}/{SUIN_JURISCOL_DATASET}.json"
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error buscando norma en datos.gov.co: {e}")
            return []

    async def fetch_norm(self, tipo: str, numero: int, anio: int) -> Optional[dict]:
        """Obtiene metadatos de una norma desde SUIN-Juriscol."""
        results = await self.search_norma(tipo, numero, anio)
        if not results:
            return None

        item = results[0]
        return {
            "tipo": item.get("tipo", tipo),
            "numero": numero,
            "anio": anio,
            "titulo": item.get("subtipo", ""),
            "estado": item.get("vigencia", ""),
            "sector": item.get("sector", ""),
            "entidad": item.get("entidad", ""),
            "fuente_url": None,
            "texto_completo": None,  # SUIN solo tiene metadatos, no texto completo
            "metadata": item,
        }

    # --- Corte Constitucional: Sentencias ---

    async def search_sentencias_cc(self, query: str, limit: int = 10,
                                    tipo_sentencia: Optional[str] = None,
                                    desde: Optional[str] = None) -> list[LiveSourceResult]:
        """
        Busca sentencias de la Corte Constitucional.

        Args:
            query: Texto de búsqueda
            limit: Máximo de resultados
            tipo_sentencia: T (tutela), C (constitucionalidad), SU (unificación)
            desde: Fecha desde (YYYY-MM-DD)
        """
        params = {
            "$q": query,
            "$limit": str(limit),
        }

        where_parts = []
        if tipo_sentencia:
            where_parts.append(f"sentencia_tipo='{tipo_sentencia.upper()}'")
        if desde:
            where_parts.append(f"fecha_sentencia>='{desde}'")
        if where_parts:
            params["$where"] = " AND ".join(where_parts)

        try:
            client = await self._get_client()
            url = f"{BASE_API_URL}/{CORTE_CC_DATASET}.json"
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data:
                numero = item.get("sentencia", "")
                results.append(LiveSourceResult(
                    source="datos_gov_cc",
                    tipo=item.get("sentencia_tipo", ""),
                    numero=None,
                    anio=None,
                    titulo=f"Sentencia {numero}",
                    estado="PRECEDENTE" if item.get("sentencia_tipo") == "SU" else None,
                    url=None,
                    preview=f"Corte Constitucional - {numero} - Mag. {item.get('magistrado_a', '')}",
                    metadata={
                        "proceso": item.get("proceso", ""),
                        "expediente_tipo": item.get("expediente_tipo", ""),
                        "expediente_numero": item.get("expediente_numero", ""),
                        "magistrado": item.get("magistrado_a", ""),
                        "sala": item.get("sala", ""),
                        "fecha": item.get("fecha_sentencia", ""),
                    }
                ))

            logger.info(f"datos.gov.co CC: {len(results)} sentencias encontradas para '{query}'")
            return results

        except httpx.HTTPError as e:
            logger.error(f"Error consultando datos.gov.co CC: {e}")
            return []

    async def is_available(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get(
                f"{BASE_API_URL}/{SUIN_JURISCOL_DATASET}.json",
                params={"$limit": "1"}
            )
            return response.status_code == 200
        except Exception:
            return False
