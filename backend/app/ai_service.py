from openai import OpenAI

def generar_respuesta_legal(pregunta: str, contexto_legal: str) -> str:
    """Envía la ley encontrada y la pregunta al modelo de IA local."""
    ia_local = OpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="lm-studio"
    )
    
    instrucciones = f"""
    Eres un experto asesor jurídico de Tamaulipas, México. Utiliza la información proporcionada en el 
    CONTEXTO RECUPERADO para responder a la pregunta del usuario de forma clara y profesional. Si la pregunta 
    hace referencia a leyes generales (como la Constitución), asume que el usuario se refiere al marco legal de 
    Tamaulipas contenido en tus documentos. Si de plano la respuesta no está en el contexto, indica educadamente 
    que tu base de datos actual no abarca ese punto exacto.

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