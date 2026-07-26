import chromadb
from sentence_transformers import SentenceTransformer

# Cargamos el mismo modelo traductor que se usó para construir la base de datos
modelo_embeddings = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

def buscar_ley(pregunta: str) -> str:
    """Busca en la base de datos vectorial el artículo más relevante."""
    client = chromadb.PersistentClient(path="./data/chroma_db")
    
    # Cambiamos al nombre correcto de la colección
    collection = client.get_or_create_collection(name="leyes_tamaulipas")
    
    # Traducimos la pregunta del usuario a vectores antes de buscar
    embedding_pregunta = modelo_embeddings.encode([pregunta]).tolist()
    
    resultados = collection.query(
        query_embeddings=embedding_pregunta,
        n_results=1
    )
    
    if resultados['documents'] and resultados['documents'][0]:
        # Extraemos el metadato para saber qué ley es y el texto del documento
        metadatos = resultados['metadatas'][0][0]
        texto = resultados['documents'][0][0]
        
        referencia = f"{metadatos.get('ordenamiento', 'Ley')} - Art. {metadatos.get('numero_articulo', '')}"
        
        # Devolvemos el contexto enriquecido a la IA
        return f"[{referencia}]\n{texto}"
    
    return "No se encontró información legal al respecto."