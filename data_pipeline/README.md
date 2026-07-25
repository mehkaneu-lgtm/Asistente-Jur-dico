# Data Pipeline

## Generar los datos desde cero
1. Coloca los PDFs en `data/raw_pdfs/`
2. `py parse_leyes_v2.py` → genera `data/clean_text_v2/*.json`
3. `py build_vector_store.py` → genera `data/chroma_db/`

## Para el equipo de backend
- Vector store persistente en: `data/chroma_db/`
- Colección: `leyes_tamaulipas`
- Import: `from build_vector_store import buscar`
- Uso: `buscar(coleccion, modelo, "pregunta del usuario", k=5)`
- Cada resultado trae metadata: `ordenamiento`, `numero_articulo`, `titulo`, `capitulo`, `estado_vigencia` 