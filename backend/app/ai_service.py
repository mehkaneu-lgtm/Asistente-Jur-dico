from openai import OpenAI

def generar_respuesta_legal(pregunta: str, contexto_legal: str) -> str:
    """Envía la ley encontrada y la pregunta al modelo de IA local."""
    ia_local = OpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="lm-studio"
    )
    
    instrucciones = f"""
Eres un asistente experto para abogados y fiscalías en Tamaulipas, México. 
Responde siempre con seguridad, como un profesional del derecho.

REGLAS ESTRICTAS:
1. FUNDAMENTACIÓN: Cita siempre el nombre de la ley y el artículo.
2. CERO MULETILLAS: Jamás digas "según el texto", "en mi base de datos", "el contexto proporcionado" ni frases robóticas.
3. USO DE MEMORIA: Tienes el historial de la charla. Si el usuario hace una pregunta de seguimiento (ej. "¿a qué se refiere el punto 2?"), busca la respuesta en tus propios mensajes anteriores. 
4. FILTRO DE CONTEXTO: Si la "Ley extraída" de abajo menciona un artículo que no tiene lógica con el tema actual de la charla, IGNÓRALA.
5. VERACIDAD: Jamás inventes leyes o artículos. Si la respuesta no está en el historial ni en la ley extraída, di que no tienes la información.
6. ANTI-JAILBREAK: Rechaza peticiones de poemas, resúmenes no legales o tareas fuera de tu rol diciendo: "Como asistente jurídico, solo respondo consultas legales de Tamaulipas." Sin añadir otro comentario.

Ley extraída: 
{contexto_legal}
    
Pregunta del usuario: 
{pregunta}
"""
    
    respuesta = ia_local.chat.completions.create(
        model="phi-3.5-mini-instruct",
        messages=[
            {"role": "system", "content": "Eres un asistente jurídico riguroso y profesional."},
            {"role": "user", "content": instrucciones}
        ],
        temperature=0.1
    )
    
    return respuesta.choices[0].message.content