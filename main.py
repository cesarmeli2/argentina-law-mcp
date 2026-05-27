"""
Argentina Legal Law MCP Server
Servidor MCP para profesionales jurídicos argentinos.
Fuentes: Infoleg, SAIJ, Boletín Oficial, iJudicial
"""

import httpx
import asyncio
from bs4 import BeautifulSoup
from fastmcp import FastMCP
from typing import Optional

mcp = FastMCP(
    name="argentina-legal-law",
    instructions="""
    Servidor MCP especializado en derecho argentino.
    Provee acceso a normas (Infoleg), jurisprudencia (SAIJ),
    Boletín Oficial, glosario jurídico (iJudicial) y análisis
    de documentos legales con IA.
    """
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ArgentineLegalBot/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
}

TIMEOUT = 20.0


# ─────────────────────────────────────────────
# TOOL 1: Buscar norma en Infoleg
# ─────────────────────────────────────────────

@mcp.tool
async def buscar_norma(
    texto: str,
    tipo: Optional[str] = None,
    limit: int = 10
) -> dict:
    """
    Busca normas argentinas en Infoleg por texto libre.

    Args:
        texto: Texto a buscar (ej: "contrato de trabajo", "ley 20744")
        tipo: Tipo de norma opcional: "ley", "decreto", "resolucion", "disposicion"
        limit: Cantidad máxima de resultados (default 10, max 50)
    """
    limit = min(limit, 50)

    # Infoleg búsqueda avanzada
    params = {
        "word": texto,
        "pageSize": limit,
        "submit": "Buscar",
    }
    if tipo:
        tipo_map = {
            "ley": "LEY",
            "decreto": "DECRETO",
            "resolucion": "RESOLUCION",
            "disposicion": "DISPOSICION",
        }
        params["tipoNorma"] = tipo_map.get(tipo.lower(), tipo.upper())

    url = "https://www.infoleg.gob.ar/infolegInternet/buscarNormas.do"

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        resultados = []

        # Parseo tabla de resultados Infoleg
        filas = soup.select("table.tabla tr")
        for fila in filas[1:]:  # skip header
            celdas = fila.find_all("td")
            if len(celdas) < 4:
                continue
            link = celdas[0].find("a")
            norma_id = link["href"].split("id=")[-1] if link and "id=" in link.get("href", "") else ""
            resultados.append({
                "titulo": celdas[0].get_text(strip=True),
                "url": f"https://www.infoleg.gob.ar/infolegInternet/anexos/{norma_id}",
                "url_texto": f"https://www.infoleg.gob.ar/infolegInternet/verNorma.do?id={norma_id}",
                "fecha": celdas[1].get_text(strip=True) if len(celdas) > 1 else "",
                "organismo": celdas[2].get_text(strip=True) if len(celdas) > 2 else "",
                "resumen": celdas[3].get_text(strip=True) if len(celdas) > 3 else "",
                "fuente": "Infoleg",
            })

        return {
            "query": texto,
            "total": len(resultados),
            "resultados": resultados,
            "fuente": "https://www.infoleg.gob.ar",
        }

    except httpx.HTTPError as e:
        return {"error": f"Error HTTP al consultar Infoleg: {str(e)}", "query": texto}
    except Exception as e:
        return {"error": f"Error inesperado: {str(e)}", "query": texto}


# ─────────────────────────────────────────────
# TOOL 2: Obtener texto de una norma por ID
# ─────────────────────────────────────────────

@mcp.tool
async def obtener_norma(
    norma_id: str,
    articulo: Optional[str] = None
) -> dict:
    """
    Obtiene el texto completo de una norma de Infoleg por su ID numérico.
    Opcionalmente filtra por número de artículo.

    Args:
        norma_id: ID numérico de la norma en Infoleg (ej: "25885" para LCT)
        articulo: Número de artículo a extraer (ej: "14", "14 bis")
    """
    url = f"https://www.infoleg.gob.ar/infolegInternet/verNorma.do?id={norma_id}"

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Título de la norma
        titulo_tag = soup.find("h1") or soup.find("h2") or soup.find("title")
        titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Sin título"

        # Contenido principal
        contenido_div = (
            soup.find("div", {"id": "normativa"})
            or soup.find("div", {"class": "norma"})
            or soup.find("div", {"id": "contenido"})
            or soup.find("body")
        )
        texto_completo = contenido_div.get_text(separator="\n", strip=True) if contenido_div else ""

        # Filtrar por artículo si se solicitó
        if articulo:
            lineas = texto_completo.split("\n")
            articulo_norm = articulo.strip().upper()
            extracto = []
            capturando = False
            for linea in lineas:
                linea_upper = linea.strip().upper()
                # Detecta inicio del artículo
                if (f"ART. {articulo_norm}" in linea_upper
                        or f"ARTÍCULO {articulo_norm}" in linea_upper
                        or f"ARTICULO {articulo_norm}" in linea_upper):
                    capturando = True
                # Detecta inicio del siguiente artículo (para de capturar)
                elif capturando and linea_upper.startswith(("ART.", "ARTÍCULO", "ARTICULO")):
                    break
                if capturando:
                    extracto.append(linea.strip())

            return {
                "norma_id": norma_id,
                "titulo": titulo,
                "articulo_solicitado": articulo,
                "texto": "\n".join(extracto) if extracto else f"Artículo {articulo} no encontrado en el texto.",
                "url": url,
                "fuente": "Infoleg",
            }

        return {
            "norma_id": norma_id,
            "titulo": titulo,
            "texto": texto_completo[:8000],  # tope razonable
            "texto_completo_disponible": len(texto_completo) > 8000,
            "url": url,
            "fuente": "Infoleg",
        }

    except httpx.HTTPError as e:
        return {"error": f"Error HTTP: {str(e)}", "norma_id": norma_id}
    except Exception as e:
        return {"error": f"Error inesperado: {str(e)}", "norma_id": norma_id}


# ─────────────────────────────────────────────
# TOOL 3: Buscar en SAIJ
# ─────────────────────────────────────────────

@mcp.tool
async def buscar_jurisprudencia(
    texto: str,
    tipo_documento: str = "jurisprudencia",
    limit: int = 10
) -> dict:
    """
    Busca jurisprudencia y legislación en SAIJ (Sistema Argentino de Información Jurídica).

    Args:
        texto: Términos de búsqueda
        tipo_documento: "jurisprudencia", "legislacion", "doctrina" (default: jurisprudencia)
        limit: Cantidad de resultados (default 10)
    """
    url = "https://www.saij.gob.ar/busqueda"
    params = {
        "tipo-documento": tipo_documento,
        "texto": texto,
        "cantidad": limit,
    }

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        resultados = []

        # SAIJ lista resultados en elementos con clase "resultado" o similar
        items = (
            soup.select(".resultado-item")
            or soup.select(".search-result")
            or soup.select("article")
            or soup.select(".item-resultado")
        )

        for item in items[:limit]:
            link = item.find("a")
            titulo = link.get_text(strip=True) if link else item.get_text(strip=True)[:100]
            href = link["href"] if link else ""
            url_item = f"https://www.saij.gob.ar{href}" if href.startswith("/") else href

            # Metadatos adicionales
            fecha_tag = item.find(class_=lambda c: c and "fecha" in c.lower()) if item else None
            tribunal_tag = item.find(class_=lambda c: c and "tribunal" in c.lower()) if item else None

            resultados.append({
                "titulo": titulo,
                "url": url_item,
                "fecha": fecha_tag.get_text(strip=True) if fecha_tag else "",
                "tribunal": tribunal_tag.get_text(strip=True) if tribunal_tag else "",
                "resumen": item.get_text(separator=" ", strip=True)[:300],
                "fuente": "SAIJ",
            })

        return {
            "query": texto,
            "tipo": tipo_documento,
            "total": len(resultados),
            "resultados": resultados,
            "fuente": "https://www.saij.gob.ar",
        }

    except httpx.HTTPError as e:
        return {"error": f"Error HTTP al consultar SAIJ: {str(e)}", "query": texto}
    except Exception as e:
        return {"error": f"Error inesperado: {str(e)}", "query": texto}


# ─────────────────────────────────────────────
# TOOL 4: Consultar Boletín Oficial
# ─────────────────────────────────────────────

@mcp.tool
async def consultar_boletin_oficial(
    texto: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    seccion: Optional[str] = None
) -> dict:
    """
    Busca publicaciones en el Boletín Oficial de la República Argentina.

    Args:
        texto: Texto a buscar en publicaciones
        fecha_desde: Fecha inicio en formato YYYY-MM-DD
        fecha_hasta: Fecha fin en formato YYYY-MM-DD
        seccion: "primera" (leyes/decretos), "segunda" (sociedades), "tercera" (avisos)
    """
    url = "https://www.boletinoficial.gob.ar/busquedaAvanzada/buscar"

    params = {}
    if texto:
        params["textoBuscado"] = texto
    if fecha_desde:
        params["fechaDesde"] = fecha_desde.replace("-", "/")
    if fecha_hasta:
        params["fechaHasta"] = fecha_hasta.replace("-", "/")
    if seccion:
        seccion_map = {"primera": "1", "segunda": "2", "tercera": "3"}
        params["seccion"] = seccion_map.get(seccion.lower(), seccion)

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        resultados = []

        items = (
            soup.select(".aviso")
            or soup.select(".resultado-boletin")
            or soup.select(".item-aviso")
            or soup.select("article")
        )

        for item in items[:20]:
            link = item.find("a")
            titulo = link.get_text(strip=True) if link else item.get_text(strip=True)[:120]
            href = link["href"] if link else ""
            url_item = f"https://www.boletinoficial.gob.ar{href}" if href.startswith("/") else href

            resultados.append({
                "titulo": titulo,
                "url": url_item,
                "texto_breve": item.get_text(separator=" ", strip=True)[:300],
                "fuente": "Boletín Oficial",
            })

        return {
            "query": texto or "(sin texto, búsqueda por fecha/sección)",
            "total": len(resultados),
            "resultados": resultados,
            "fuente": "https://www.boletinoficial.gob.ar",
        }

    except httpx.HTTPError as e:
        return {"error": f"Error HTTP al consultar Boletín Oficial: {str(e)}"}
    except Exception as e:
        return {"error": f"Error inesperado: {str(e)}"}


# ─────────────────────────────────────────────
# TOOL 5: Explicar término jurídico
# ─────────────────────────────────────────────

@mcp.tool
async def explicar_termino(termino: str) -> dict:
    """
    Explica un término jurídico usando el glosario oficial del Poder Judicial argentino (iJudicial).

    Args:
        termino: Término jurídico a consultar (ej: "acción de amparo", "litispendencia")
    """
    # iJudicial - glosario del PJN
    url = "https://ijudicial.gob.ar/glosario/"
    params = {"s": termino}

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Busca definiciones en el glosario
        definiciones = []
        entries = (
            soup.select(".glosario-item")
            or soup.select(".glossary-item")
            or soup.select("dt")
            or soup.select(".entry-content")
        )

        for entry in entries[:5]:
            texto = entry.get_text(separator=" ", strip=True)
            if termino.lower() in texto.lower() or len(definiciones) == 0:
                definiciones.append(texto[:500])

        if not definiciones:
            # Fallback: todo el contenido principal
            main = soup.find("main") or soup.find("article") or soup.find("body")
            if main:
                definiciones = [main.get_text(separator=" ", strip=True)[:1000]]

        return {
            "termino": termino,
            "definiciones": definiciones,
            "fuente": "iJudicial - Poder Judicial de la Nación",
            "url": f"https://ijudicial.gob.ar/glosario/?s={termino}",
        }

    except httpx.HTTPError as e:
        return {"error": f"Error HTTP: {str(e)}", "termino": termino}
    except Exception as e:
        return {"error": f"Error inesperado: {str(e)}", "termino": termino}


# ─────────────────────────────────────────────
# TOOL 6: Analizar documento jurídico (IA)
# ─────────────────────────────────────────────

@mcp.tool
async def analizar_documento(
    texto_documento: str,
    tipo_documento: Optional[str] = None,
    instruccion: Optional[str] = None
) -> dict:
    """
    Analiza un documento jurídico argentino usando IA (Claude).
    Identifica partes, obligaciones, plazos, riesgos y cláusulas problemáticas.

    Args:
        texto_documento: Texto completo del documento a analizar
        tipo_documento: Tipo de documento (ej: "contrato", "sentencia", "telegrama", "CCT", "acta acuerdo")
        instruccion: Instrucción específica de análisis (ej: "identificar cláusulas nulas", "extraer plazos")
    """
    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY no configurada en el servidor."}

    tipo_str = tipo_documento or "documento jurídico"
    instruccion_str = instruccion or "análisis general: partes, objeto, obligaciones, plazos, riesgos y cláusulas problemáticas"

    system_prompt = """Sos un asistente de análisis jurídico especializado en derecho argentino.
Respondés siempre en español rioplatense, registro forense.
Sos preciso, no inventás normas ni jurisprudencia.
Cuando identifiques riesgos o problemas, los señalás con claridad.
No usás disclaimers ni advertencias genéricas - el usuario es un abogado matriculado."""

    user_prompt = f"""Analizá el siguiente {tipo_str} según el derecho argentino vigente.

INSTRUCCIÓN ESPECÍFICA: {instruccion_str}

DOCUMENTO:
{texto_documento[:6000]}

Estructurá tu respuesta en:
1. IDENTIFICACIÓN: tipo de acto, partes, fecha, objeto
2. ANÁLISIS: desarrollo según la instrucción
3. ALERTAS: problemas, vacíos, cláusulas cuestionables
4. REFERENCIAS NORMATIVAS: normas aplicables (sin inventar - solo las que conocés con certeza)"""

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1500,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        analisis = data["content"][0]["text"] if data.get("content") else "Sin respuesta."

        return {
            "tipo_documento": tipo_str,
            "instruccion": instruccion_str,
            "analisis": analisis,
            "tokens_usados": data.get("usage", {}),
            "modelo": "claude-sonnet-4-20250514",
        }

    except httpx.HTTPError as e:
        return {"error": f"Error al llamar API Anthropic: {str(e)}"}
    except Exception as e:
        return {"error": f"Error inesperado: {str(e)}"}


# ─────────────────────────────────────────────
# TOOL 7: Normas más relevantes (IDs conocidos)
# ─────────────────────────────────────────────

@mcp.tool
async def normas_frecuentes(area: str) -> dict:
    """
    Devuelve las normas más relevantes para un área del derecho laboral/civil argentino,
    con sus IDs de Infoleg para consulta directa.

    Args:
        area: Área del derecho: "laboral", "accidentes_trabajo", "concursos",
              "sociedades", "contratos", "familia", "penal", "administrativo"
    """
    catalogo = {
        "laboral": [
            {"nombre": "Ley de Contrato de Trabajo N° 20.744", "infoleg_id": "25885", "numero": "20744"},
            {"nombre": "Ley de Empleo N° 24.013", "infoleg_id": "416", "numero": "24013"},
            {"nombre": "Ley 25.877 (Ordenamiento Laboral)", "infoleg_id": "93970", "numero": "25877"},
            {"nombre": "Ley 27.742 (Desregulación)", "infoleg_id": "401132", "numero": "27742"},
            {"nombre": "Ley 27.802 (Paritarias)", "infoleg_id": "406000", "numero": "27802"},
            {"nombre": "CCT Marco Bebidas Gaseosas N° 152/91", "infoleg_id": None, "numero": "CCT 152/91"},
        ],
        "accidentes_trabajo": [
            {"nombre": "Ley de Riesgos del Trabajo N° 24.557", "infoleg_id": "27971", "numero": "24557"},
            {"nombre": "Ley 26.773 (Régimen de ordenamiento LRT)", "infoleg_id": "201451", "numero": "26773"},
            {"nombre": "Ley 27.348 (Complementaria LRT)", "infoleg_id": "271740", "numero": "27348"},
            {"nombre": "Decreto 659/96 (Tabla de incapacidades)", "infoleg_id": "37734", "numero": "659/96"},
            {"nombre": "Decreto 472/14 (Actualización prestaciones)", "infoleg_id": "227133", "numero": "472/14"},
        ],
        "concursos": [
            {"nombre": "Ley de Concursos y Quiebras N° 24.522", "infoleg_id": "1357", "numero": "24522"},
        ],
        "sociedades": [
            {"nombre": "Ley General de Sociedades N° 19.550", "infoleg_id": "25155", "numero": "19550"},
        ],
        "contratos": [
            {"nombre": "Código Civil y Comercial N° 26.994", "infoleg_id": "235975", "numero": "26994"},
        ],
        "familia": [
            {"nombre": "Código Civil y Comercial N° 26.994", "infoleg_id": "235975", "numero": "26994"},
        ],
        "penal": [
            {"nombre": "Código Penal N° 11.179", "infoleg_id": "16546", "numero": "11179"},
            {"nombre": "Código Procesal Penal Federal N° 27.063", "infoleg_id": "246551", "numero": "27063"},
        ],
        "administrativo": [
            {"nombre": "Ley de Procedimientos Administrativos N° 19.549", "infoleg_id": "17234", "numero": "19549"},
            {"nombre": "Ley 27.742 (Desregulación - RIGI)", "infoleg_id": "401132", "numero": "27742"},
        ],
    }

    area_norm = area.lower().replace(" ", "_")
    normas = catalogo.get(area_norm)

    if not normas:
        areas_disponibles = list(catalogo.keys())
        return {
            "error": f"Área '{area}' no encontrada.",
            "areas_disponibles": areas_disponibles,
        }

    # Agrega URLs directas
    for n in normas:
        if n["infoleg_id"]:
            n["url_texto"] = f"https://www.infoleg.gob.ar/infolegInternet/verNorma.do?id={n['infoleg_id']}"
        else:
            n["url_texto"] = f"https://www.infoleg.gob.ar/infolegInternet/buscarNormas.do?word={n['numero']}"

    return {
        "area": area,
        "total": len(normas),
        "normas": normas,
        "nota": "IDs verificados al momento de construcción del servidor. Verificar vigencia actual.",
    }


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port, path="/mcp")
