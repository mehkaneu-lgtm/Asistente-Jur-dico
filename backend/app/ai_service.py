from openai import OpenAI

def generar_respuesta_legal(pregunta: str, contexto_legal: str) -> str:
    """Envía la ley encontrada y la pregunta al modelo de IA local."""
    ia_local = OpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="lm-studio"
    )
    
    instrucciones = f"""
    Eres un asesor legal mexicano. Responde a la pregunta del usuario utilizando ÚNICAMENTE la siguiente ley.
    Si la ley no responde la pregunta, di que no tienes información suficiente.

    Ley extraída: {contexto_legal}
    
    Pregunta del usuario: {pregunta}
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