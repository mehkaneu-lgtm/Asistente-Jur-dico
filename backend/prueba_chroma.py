import chromadb
from openai import OpenAI

# 1. Configurar tu conexión a LM Studio (Fingiendo ser la API de OpenAI)
# Usamos 127.0.0.1 como vimos en tu pantalla para evitar bloqueos de Windows
ia_local = OpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio" 
)

# 2. Inicializar el cliente de ChromaDB
client = chromadb.PersistentClient(path="./backend/chroma_db")
collection = client.get_or_create_collection(name="leyes_prueba")

# 3. Inyectar datos de prueba
print("Guardando leyes en la base de datos...\n")
collection.add(
    documents=[
        "Artículo 1. En los Estados Unidos Mexicanos todas las personas gozarán de los derechos humanos.",
        "Artículo 367. Comete el delito de robo: el que se apodera de una cosa ajena mueble, sin derecho y sin consentimiento."
    ],
    metadatas=[
        {"fuente": "Constitucion", "tipo": "Derechos Humanos"}, 
        {"fuente": "Codigo Penal", "tipo": "Delito Patrimonial"}
    ],
    ids=["doc_1", "doc_2"]
)

# 4. Hacer tu consulta RAG a la Base de Datos
pregunta_del_abogado = input("En que puedo ayudarte hoy? (Escribe tu pregunta legal): ")
print(f"Buscando respuesta en la base de datos para: '{pregunta_del_abogado}'...")

resultados = collection.query(
    query_texts=[pregunta_del_abogado],
    n_results=1
)
ley_encontrada = resultados['documents'][0][0]
print(f"✅ Ley encontrada exitosamente.\n")

# 5. Construir las instrucciones para tu IA (El Prompt)
instrucciones = f"""
Eres un asesor legal mexicano. Responde a la pregunta del usuario utilizando ÚNICAMENTE la siguiente ley extraída de la base de datos.
Si la ley no responde la pregunta, di que no tienes información suficiente.

Ley extraída: {ley_encontrada}

Pregunta del usuario: {pregunta_del_abogado}
"""

# 6. Mandar a generar la respuesta a LM Studio
print("Consultando a LM Studio (Phi-3.5) para redactar la respuesta final...\n")
respuesta = ia_local.chat.completions.create(
    model="phi-3.5-mini-instruct", 
    messages=[
        {"role": "system", "content": "Eres un asistente jurídico riguroso y profesional."},
        {"role": "user", "content": instrucciones}
    ],
    temperature=0.1 
)

# 7. Imprimir el resultado final
print("--- RESPUESTA DEL ASESOR ---")
print(respuesta.choices[0].message.content)