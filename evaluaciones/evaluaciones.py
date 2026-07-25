# Programa principal de evaluaciones.

from pathlib import Path

try:
    from .casos_prueba import CASOS
    from .evaluador import evaluar_caso, guardar_resultados
except ImportError:  # Permite ejecutarlo como script simple.
    from casos_prueba import CASOS
    from evaluador import evaluar_caso, guardar_resultados


def preguntar_backend(pregunta: str) -> str:
    """Punto de entrada temporal para el backend.

    Más adelante este método se reemplazará por una llamada real al backend
    o a la API del sistema.
    """
    return "Respuesta simulada para la evaluación del sistema."


def ejecutar_evaluaciones() -> list[dict]:
    """Ejecuta todos los casos de prueba y guarda los resultados."""
    resultados = []
    for caso in CASOS:
        print(f"Evaluando: {caso['nombre']}")
        respuesta = preguntar_backend(caso["pregunta"])
        resultado = evaluar_caso(caso, respuesta)
        resultados.append(resultado)
        estado = "✅ Aprobado" if resultado["evaluacion"]["aprobado"] else "❌ Rechazado"
        print(f"  {estado}: {respuesta}")

    guardar_resultados(resultados)
    print(f"Resultados guardados en {Path('evaluaciones/resultados.txt').resolve()}")
    return resultados


if __name__ == "__main__":
    ejecutar_evaluaciones()