from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Importamos las funciones que acabas de crear en los otros archivos
from app.rag_service import buscar_ley
from app.ai_service import generar_respuesta_legal

app = FastAPI(title="Asistente Jurídico API")

# Configuración de CORS (Vital para que el Frontend se pueda conectar sin bloqueos)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Definimos cómo debe llegar la pregunta desde el Frontend
class ConsultaAbogado(BaseModel):
    pregunta: str

@app.post("/consultar")
def consultar_asistente(consulta: ConsultaAbogado):
    # 1. Recuperar la ley (R)
    ley_encontrada = buscar_ley(consulta.pregunta)
    
    # 2. Generar la respuesta con Phi-3.5 (G)
    respuesta_ia = generar_respuesta_legal(consulta.pregunta, ley_encontrada)
    
    # 3. Devolver un JSON estructurado a José
    return {
        "respuesta": respuesta_ia,
        "ley_citada": ley_encontrada
    }