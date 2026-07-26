"""
Pipeline: JSON de leyes -> chunks -> embeddings -> ChromaDB
Requiere: pip install chromadb sentence-transformers --break-system-packages
"""
import json
import os
import chromadb 

CLEAN_DIR = "data/clean_text_v2"
DB_DIR = "data/chroma_db"
MAX_CARACTERES_CHUNK = 1800  # ~450 tokens aprox, margen cómodo para modelos de embeddings

LEYES = [
    "constitucion_tamaulipas.json",
    "codigo_penal_tamaulipas.json",
    "codigo_civil_tamaulipas.json",
]


def construir_encabezado_contexto(articulo: dict, ordenamiento: str) -> str:
    """Prefijo de contexto para que el embedding no confunda, ej., el Art. 1
    del Código Penal con el Art. 1 del Código Civil (recomendación que ya tenían)."""
    partes = [ordenamiento]
    if articulo.get("titulo"):
        partes.append(articulo["titulo"])
    if articulo.get("capitulo"):
        partes.append(articulo["capitulo"])
    partes.append(f"Art. {articulo['numero_articulo']}")
    return f"[{' - '.join(partes)}]"


def dividir_si_es_muy_largo(texto: str, max_len: int = MAX_CARACTERES_CHUNK) -> list[str]:
    """La mayoría de los artículos caben en un solo chunk (ideal, ver mejores
    prácticas). Solo se parte si un artículo es inusualmente largo, cortando
    por punto y seguido cerca del límite para no partir oraciones a la mitad."""
    if len(texto) <= max_len:
        return [texto]
    partes = []
    resto = texto
    while len(resto) > max_len:
        corte = resto.rfind(". ", 0, max_len)
        if corte == -1:
            corte = max_len
        partes.append(resto[:corte + 1].strip())
        resto = resto[corte + 1:].strip()
    if resto:
        partes.append(resto)
    return partes


def cargar_chunks() -> list[dict]:
    chunks = []
    for archivo in LEYES:
        ruta = os.path.join(CLEAN_DIR, archivo)
        if not os.path.exists(ruta):
            print(f"[falta] {ruta}")
            continue
        with open(ruta, encoding="utf-8") as f:
            data = json.load(f)

        ordenamiento = data["metadatos_documento"]["ordenamiento"]
        materia = data["metadatos_documento"]["materia"]

        for art in data["articulos"]:
            encabezado = construir_encabezado_contexto(art, ordenamiento)
            partes_texto = dividir_si_es_muy_largo(art["texto_completo"])

            for i, parte in enumerate(partes_texto):
                sufijo_parte = f" (parte {i + 1}/{len(partes_texto)})" if len(partes_texto) > 1 else ""
                texto_final = f"{encabezado}{sufijo_parte}\n{parte}"

                chunks.append({
                    "id": f"{art['id']}" + (f"_p{i+1}" if len(partes_texto) > 1 else ""),
                    "texto": texto_final,
                    "metadata": {
                        "ordenamiento": ordenamiento,
                        "materia": materia,
                        "articulo_id": art["id"],
                        "numero_articulo": art["numero_articulo"],
                        "titulo": art.get("titulo") or "",
                        "capitulo": art.get("capitulo") or "",
                        "estado_vigencia": art["estado_vigencia"],
                    },
                })
    return chunks


def construir_vector_store(chunks: list[dict]):
    from sentence_transformers import SentenceTransformer
    modelo = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")  # ligero, soporta español

    client = chromadb.PersistentClient(path=DB_DIR)
    # si ya existe de una corrida anterior, se recrea limpio
    try:
        client.delete_collection("leyes_tamaulipas")
    except Exception:
        pass
    coleccion = client.create_collection("leyes_tamaulipas")

    textos = [c["texto"] for c in chunks]
    print(f"Generando embeddings para {len(textos)} chunks...")
    embeddings = modelo.encode(textos, show_progress_bar=True, batch_size=64).tolist()

    # Chroma tiene límite de batch; se inserta en lotes de 500
    LOTE = 500
    for i in range(0, len(chunks), LOTE):
        lote = chunks[i:i + LOTE]
        coleccion.add(
            ids=[c["id"] for c in lote],
            documents=[c["texto"] for c in lote],
            embeddings=embeddings[i:i + LOTE],
            metadatas=[c["metadata"] for c in lote],
        )
    print(f"✓ {len(chunks)} chunks guardados en {DB_DIR}")
    return coleccion, modelo


def buscar(coleccion, modelo, pregunta: str, k: int = 5, filtro_ordenamiento: str | None = None):
    embedding_pregunta = modelo.encode([pregunta]).tolist()
    where = {"ordenamiento": filtro_ordenamiento} if filtro_ordenamiento else None
    resultados = coleccion.query(
        query_embeddings=embedding_pregunta,
        n_results=k,
        where=where,
    )
    return resultados
def buscar_articulo_exacto(coleccion, numero_articulo: str, ordenamiento: str | None = None):
    """Búsqueda directa cuando se conoce el número de artículo exacto,
    en vez de depender de similitud semántica."""
    where = {"numero_articulo": numero_articulo}
    if ordenamiento:
        where = {"$and": [{"numero_articulo": numero_articulo}, {"ordenamiento": ordenamiento}]}
    return coleccion.get(where=where)

if __name__ == "__main__":
    chunks = cargar_chunks()
    print(f"Total de chunks a indexar: {len(chunks)}")
    coleccion, modelo = construir_vector_store(chunks)

    # prueba rápida
    pregunta = "¿Qué pasa si cambia la ley durante la comisión de un delito?"
    resultados = buscar(coleccion, modelo, pregunta, k=3)
    print(f"\nPregunta: {pregunta}")
    for doc, meta in zip(resultados["documents"][0], resultados["metadatas"][0]):
        print(f"\n[{meta['ordenamiento']} - Art. {meta['numero_articulo']}]")
        print(doc[:200])