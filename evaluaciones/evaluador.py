# Funciones auxiliares para evaluar respuestas del asistente

from typing import List, Dict


def evaluar_respuesta(respuesta: str, respuesta_esperada: str) -> Dict[str, object]:
    """Evalúa si una respuesta contiene palabras clave relevantes."""
    respuesta = respuesta.lower()
    respuesta_esperada = respuesta_esperada.lower()

    palabras_clave = [palabra for palabra in respuesta_esperada.split() if len(palabra) > 3]
    coincidencias = sum(1 for palabra in palabras_clave if palabra in respuesta)

    return {
        "coincidencias": coincidencias,
        "total_palabras_clave": len(palabras_clave),
        "aprobado": coincidencias >= max(1, len(palabras_clave) // 2)
    }


def evaluar_casos(casos: List[Dict[str, object]], respuestas: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Evalúa una lista de casos con sus respuestas."""
    resultados = []
    for caso, respuesta in zip(casos, respuestas):
        evaluacion = evaluar_respuesta(
            respuesta.get("respuesta", ""),
            caso.get("respuesta_esperada", "")
        )
        resultados.append({
            "id": caso.get("id"),
            "pregunta": caso.get("pregunta"),
            "respuesta": respuesta.get("respuesta", ""),
            "evaluacion": evaluacion
        })
    return resultados
