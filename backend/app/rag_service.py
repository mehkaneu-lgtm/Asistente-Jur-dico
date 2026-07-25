import chromadb

def buscar_ley(pregunta: str) -> str:
    """Busca en la base de datos vectorial el artículo más relevante."""
    client = chromadb.PersistentClient(path="./backend/chroma_db")
    collection = client.get_or_create_collection(name="leyes_prueba")
    
    resultados = collection.query(
        query_texts=[pregunta],
        n_results=1
    )
    
    if resultados['documents'] and resultados['documents'][0]:
        return resultados['documents'][0][0]
    
    return "No se encontró información legal al respecto."