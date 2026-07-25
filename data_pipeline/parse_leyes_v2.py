import re
import os
import json
import unicodedata
import pdfplumber

RAW_DIR = "data/raw_pdfs"
OUT_DIR = "data/clean_text_v2"

# --- Encabezados jerárquicos ---
LIBRO_RE = re.compile(r"^\s*LIBRO\s+[A-ZÁÉÍÓÚ]+\.?\s*$", re.MULTILINE)
TITULO_RE = re.compile(r"^\s*T[ÍI]TULO\s+[A-ZÁÉÍÓÚ0-9]+\.?\s*$", re.MULTILINE)
CAPITULO_RE = re.compile(r"^\s*CAP[ÍI]TULO\s+[A-ZÁÉÍÓÚ0-9]+\.?\s*$", re.MULTILINE)
SECCION_RE = re.compile(r"^\s*SECCI[ÓO]N\s+[A-ZÁÉÍÓÚ0-9]+\.?\s*$", re.MULTILINE)

# "ARTÍCULO 1o.-", "ARTÍCULO 12.-", "ARTÍCULO 5 Bis.-"
ARTICULO_RE = re.compile(
    r"ART[ÍI]CULO\s+(\d+)\s*[oO°]?\.?\s*(BIS|TER|QU[AÁ]TER)?\.?\s*[-–—]\s*",
    re.IGNORECASE,
)

# Fracciones tipo "I.-", "II.-", "III.-"
FRACCION_RE = re.compile(r"(?:^|\n)\s*([IVXLCDM]{1,6})\.[-–—]\s*", re.MULTILINE)

REFORMA_RE = re.compile(
    r"P\.?\s*O\.?\s*(?:Extraordinario\s*)?No\.?\s*\d+,?\s*del?\s+"
    r"(\d{1,2}\s+de\s+[A-Za-zÁÉÍÓÚáéíóú]+\s+de\s+\d{4})",
    re.IGNORECASE,
)
PORTADA_RE = re.compile(
    r"[ÚU]ltima reforma aplicada.*?(\d{1,2}\s+de\s+[A-Za-zÁÉÍÓÚáéíóú]+\s+de\s+\d{4})",
    re.IGNORECASE,
)
DEROGADO_RE = re.compile(r"^\s*Derogad[oa]s?\.", re.IGNORECASE)

MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
}


def fecha_a_iso(fecha_texto: str) -> str:
    m = re.match(r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóú]+)\s+de\s+(\d{4})", fecha_texto.strip(), re.IGNORECASE)
    if not m:
        return ""
    dia, mes_nombre, anio = m.groups()
    return f"{anio}-{MESES.get(mes_nombre.lower(), '01')}-{dia.zfill(2)}"


FOOTER_RE = re.compile(
    r"^(C[oó]digo (?:Penal|Civil) para el Estado de Tamaulipas|Constituci[oó]n Pol[ií]tica del Estado de Tamaulipas)"
    r"\s*(P[áa]g\.\s*\d+)?\s*$",
    re.IGNORECASE,
)


def quitar_pie_pagina(texto: str) -> str:
    lineas = [l for l in texto.split("\n")
              if l.strip()
              and not re.match(r"^P[áa]g\.\s*\d+$", l.strip(), re.IGNORECASE)
              and not FOOTER_RE.match(l.strip())]
    return "\n".join(lineas)


def extraer_texto_completo(pdf_path: str) -> str:
    """Extrae texto excluyendo cualquier caracter de marca de agua (fuentes/tamaños
    atípicos, ej. Arial-Black a 37-48pt detectado en estos PDFs)."""
    partes = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            limpia = page.filter(
                lambda obj: obj.get("object_type") != "char"
                or (obj.get("size", 0) <= 20 and "Black" not in obj.get("fontname", ""))
            )
            raw = limpia.extract_text() or ""
            partes.append(unicodedata.normalize("NFC", raw))
    return quitar_pie_pagina("\n".join(partes))


def titulo_descriptivo(bloque_texto: str, header_matches: list[re.Match]) -> str:
    """Devuelve el último encabezado + su línea descriptiva siguiente si la hay."""
    if not header_matches:
        return ""
    m = header_matches[-1]
    palabras = m.group(0).strip().split()
    palabras_fmt = [
        w if re.fullmatch(r"[IVXLCDM]+", w) else w.capitalize()
        for w in palabras
    ]
    encabezado = " ".join(palabras_fmt)
    resto = bloque_texto[m.end():].lstrip("\n")
    siguiente_linea = resto.split("\n", 1)[0].strip()
    # una descripción real suele venir en mayúsculas y no ser otro encabezado/artículo
    if siguiente_linea and siguiente_linea.isupper() and not re.match(
        r"^(LIBRO|T[ÍI]TULO|CAP[ÍI]TULO|SECCI[ÓO]N|ART[ÍI]CULO)\b", siguiente_linea, re.IGNORECASE
    ):
        return f"{encabezado} - {siguiente_linea}"
    return encabezado


def extraer_fracciones(cuerpo: str) -> tuple[list[dict], str]:
    """Separa fracciones (I.-, II.-, ...) del resto del párrafo introductorio."""
    matches = list(FRACCION_RE.finditer(cuerpo))
    if not matches:
        return [], cuerpo
    intro = cuerpo[:matches[0].start()].strip()
    fracciones = []
    for i, m in enumerate(matches):
        inicio = m.end()
        fin = matches[i + 1].start() if i + 1 < len(matches) else len(cuerpo)
        fracciones.append({
            "numero": m.group(1),
            "texto": " ".join(cuerpo[inicio:fin].split()),
        })
    return fracciones, intro


def parsear_ley(texto: str, ordenamiento: str, materia: str, fuente_pdf: str, prefijo_id: str) -> dict:
    portada_match = PORTADA_RE.search(texto)
    ultima_reforma_doc = fecha_a_iso(portada_match.group(1)) if portada_match else ""

    matches = list(ARTICULO_RE.finditer(texto))
    articulos = []
    libro_actual = ""
    titulo_actual = ""
    capitulo_actual = ""
    seccion_actual = ""

    for idx, m in enumerate(matches):
        inicio = m.end()
        fin = matches[idx + 1].start() if idx + 1 < len(matches) else len(texto)
        cuerpo = texto[inicio:fin].strip()

        # si un encabezado de LIBRO/TÍTULO/CAPÍTULO/SECCIÓN quedó atrapado al final
        # del cuerpo (pertenece al siguiente artículo, no a este), se recorta aquí
        primer_encabezado = None
        for header_re in (LIBRO_RE, TITULO_RE, CAPITULO_RE, SECCION_RE):
            m_h = header_re.search(cuerpo)
            if m_h and (primer_encabezado is None or m_h.start() < primer_encabezado):
                primer_encabezado = m_h.start()
        if primer_encabezado is not None:
            cuerpo = cuerpo[:primer_encabezado].strip()

        bloque_previo = texto[:m.start()]

        libros = list(LIBRO_RE.finditer(bloque_previo))
        titulos = list(TITULO_RE.finditer(bloque_previo))
        capitulos = list(CAPITULO_RE.finditer(bloque_previo))
        secciones = list(SECCION_RE.finditer(bloque_previo))

        if libros:
            libro_actual = titulo_descriptivo(bloque_previo, libros)
        if titulos:
            titulo_actual = titulo_descriptivo(bloque_previo, titulos)
        if capitulos:
            capitulo_actual = titulo_descriptivo(bloque_previo, capitulos)
        if secciones:
            seccion_actual = titulo_descriptivo(bloque_previo, secciones)

        numero = m.group(1)
        sufijo = (m.group(2) or "").capitalize()
        numero_articulo = f"{numero} {sufijo}".strip()

        reformas_raw = REFORMA_RE.findall(cuerpo)
        reformas_iso = sorted({fecha_a_iso(r) for r in reformas_raw if fecha_a_iso(r)})

        fracciones, parrafo_intro = extraer_fracciones(cuerpo)
        parrafos = [p.strip() for p in cuerpo.split("\n") if p.strip()] if not fracciones else (
            [parrafo_intro] if parrafo_intro else []
        )

        estado_vigencia = "Vigente"
        if DEROGADO_RE.search(cuerpo):
            estado_vigencia = "Derogado"
        elif reformas_iso:
            estado_vigencia = "Reformado"

        registro = {
            "id": f"{prefijo_id}-ART-{numero_articulo.replace(' ', '_')}",
            "libro": libro_actual,
            "titulo": titulo_actual,
            "capitulo": capitulo_actual,
            "seccion": seccion_actual or None,
            "numero_articulo": numero_articulo,
            "articulo_epigrafe": None,  # estos ordenamientos no traen epígrafe por artículo
            "texto_completo": f"Artículo {numero_articulo}.- " + " ".join(cuerpo.split()),
            "fracciones": fracciones,
            "parrafos": parrafos,
            "estado_vigencia": estado_vigencia,
            "ultima_reforma": reformas_iso[-1] if reformas_iso else "",
            "tags_claves": [],  # requiere un paso de enriquecimiento semántico (LLM), no se infiere por regex
        }
        articulos.append(registro)

    return {
        "metadatos_documento": {
            "ordenamiento": ordenamiento,
            "jurisdiccion": "Estatal",
            "estado": "Tamaulipas",
            "materia": materia,
            "ultima_reforma": ultima_reforma_doc,
            "fuente_pdf": fuente_pdf,
            "total_articulos": len(articulos),
        },
        "articulos": articulos,
    }


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    leyes = [
        {"pdf": "contitucion_tamaulipas.pdf", "slug": "constitucion_tamaulipas",
         "ordenamiento": "Constitución Política del Estado de Tamaulipas",
         "materia": "Constitucional", "prefijo_id": "CONST-TAM"},
        {"pdf": "codigo_penal_tamaulipas.pdf", "slug": "codigo_penal_tamaulipas",
         "ordenamiento": "Código Penal para el Estado de Tamaulipas",
         "materia": "Penal", "prefijo_id": "CP-TAM"},
        {"pdf": "codigo_civil_tamaulipas.pdf", "slug": "codigo_civil_tamaulipas",
         "ordenamiento": "Código Civil para el Estado de Tamaulipas",
         "materia": "Civil", "prefijo_id": "CC-TAM"},
    ]

    for ley in leyes:
        ruta = f"{RAW_DIR}/{ley['pdf']}"
        if not os.path.exists(ruta):
            print(f"[falta] {ruta}")
            continue
        texto = extraer_texto_completo(ruta)
        resultado = parsear_ley(texto, ley["ordenamiento"], ley["materia"], ley["pdf"], ley["prefijo_id"])
        out_path = f"{OUT_DIR}/{ley['slug']}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        print(f"✓ {ley['slug']}: {resultado['metadatos_documento']['total_articulos']} artículos → {out_path}")
        