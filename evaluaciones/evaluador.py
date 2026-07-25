# Funciones auxiliares para evaluar respuestas del asistente.

from pathlib import Path
from typing import Any, Dict, List, Optional


def evaluar(respuesta: str, respuesta_esperada: Optional[str] = None) -> Dict[str, Any]:
    """Evalúa si una respuesta es válida para el caso dado."""
    texto = (respuesta or "").strip().lower()

    if not texto:
        return {"aprobado": False, "motivo": "respuesta vacía"}

    if respuesta_esperada:
        esperado = respuesta_esperada.strip().lower()
        palabras_clave = [palabra for palabra in esperado.split() if len(palabra) > 2]
        coincidencias = sum(1 for palabra in palabras_clave if palabra in texto)
        aprobado = coincidencias >= max(1, len(palabras_clave) // 2)
        return {
            "aprobado": aprobado,
            "coincidencias": coincidencias,
            "total_palabras_clave": len(palabras_clave),
            "motivo": "coincidencia parcial" if not aprobado else "coincidencia suficiente"
        }

    return {"aprobado": True, "motivo": "respuesta no vacía"}


def evaluar_caso(caso: Dict[str, Any], respuesta: str) -> Dict[str, Any]:
    """Evalúa un caso concreto con una respuesta."""
    evaluacion = evaluar(respuesta, caso.get("respuesta_esperada"))
    return {
        "nombre": caso.get("nombre", "Sin nombre"),
        "pregunta": caso.get("pregunta", ""),
        "respuesta": respuesta,
        "evaluacion": evaluacion
    }


def guardar_resultados(resultados: List[Dict[str, Any]], ruta: str = "evaluaciones/resultados.txt") -> None:
    """Guarda los resultados en un archivo de texto."""
    archivo = Path(ruta)
    archivo.parent.mkdir(parents=True, exist_ok=True)
    with archivo.open("w", encoding="utf-8") as fh:
        for resultado in resultados:
            aprobado = "✅" if resultado["evaluacion"]["aprobado"] else "❌"
            fh.write(f"{aprobado} {resultado['nombre']}\n")
            fh.write(f"Pregunta: {resultado['pregunta']}\n")
            fh.write(f"Respuesta: {resultado['respuesta']}\n")
            fh.write(f"Detalle: {resultado['evaluacion']}\n\n")
