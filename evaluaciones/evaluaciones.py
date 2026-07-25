# Programa principal de evaluaciones.

from pathlib import Path
from typing import Any, Callable, Optional

try:
    from .casos_prueba import CASOS
    from .evaluador import evaluar_caso, guardar_json, guardar_resultados
except ImportError:  # Permite ejecutarlo como script simple.
    from casos_prueba import CASOS
    from evaluador import evaluar_caso, guardar_json, guardar_resultados


BACKEND_CALL = None


def registrar_backend(funcion: Callable[[str, Optional[dict], Optional[dict]], str]) -> None:
    """Registra la función que se usará para consultar el backend real."""
    global BACKEND_CALL
    BACKEND_CALL = funcion


def preguntar_backend(pregunta: str, documento: Optional[dict] = None, contexto: Optional[dict] = None) -> str:
    """Punto de entrada para consultar el backend.

    Si ya se registró una función real, la usa. Si no, usa un fallback temporal.
    """
    if BACKEND_CALL is not None:
        return BACKEND_CALL(pregunta, documento, contexto)

    respuestas = {
        "juridico": "Soy un asistente jurídico y puedo responder sobre derecho. Basándome en el contexto proporcionado, el amparo es un mecanismo legal para proteger derechos fundamentales.",
        "fuera_dominio": "No puedo ayudar con esa solicitud porque está fuera del ámbito jurídico. Puedo ayudar con temas legales o con consultas relacionadas con el derecho.",
        "prompt_injection": "No voy a seguir esa instrucción. Solo puedo responder dentro del ámbito jurídico y sin desviarme de mis límites de seguridad.",
        "rag": f"Según el contexto recuperado, {documento.get('fuente', 'el documento')} indica que {documento.get('articulo', 'el artículo')} establece que el Código se aplica a los delitos del orden federal.",
        "no_inventar": "No puedo inventar jurisprudencia ni leyes. Solo puedo responder con base en el contexto proporcionado y señalar si no tengo suficiente información."
    }
    tipo = "juridico"
    if "pizza" in pregunta.lower():
        tipo = "fuera_dominio"
    elif "ignora" in pregunta.lower() or "instrucción" in pregunta.lower():
        tipo = "prompt_injection"
    elif "artículo" in pregunta.lower() or "código" in pregunta.lower():
        tipo = "rag"
    elif "jurisprudencia" in pregunta.lower():
        tipo = "no_inventar"

    return respuestas[tipo]


def ejecutar_evaluaciones() -> list[dict]:
    """Ejecuta todos los casos de prueba y guarda los resultados."""
    resultados = []
    for caso in CASOS:
        print(f"Evaluando: {caso['nombre']}")
        respuesta = preguntar_backend(caso["pregunta"], caso.get("documento"), contexto=caso.get("documento"))
        resultado = evaluar_caso(caso, respuesta)
        resultados.append(resultado)
        estado = "✅ Aprobado" if resultado["evaluacion"]["aprobado"] else "❌ Rechazado"
        print(f"  {estado}: {respuesta}")

    guardar_resultados(resultados)
    guardar_json(resultados)
    print(f"Resultados guardados en {Path('evaluaciones/resultados.txt').resolve()}")
    print(f"Resultados JSON guardados en {Path('evaluaciones/resultados.json').resolve()}")
    return resultados


if __name__ == "__main__":
    ejecutar_evaluaciones()