import os
import re
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Brand Twin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tvojton.online",
        "https://www.tvojton.online",
        "http://localhost:3000",
        "http://localhost:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

class QueryRequest(BaseModel):
    query: str
    model: str = "gemma3:4b"

def detect_language(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ['čo', 'ako', 'kde', 'kto', 'je', 'som', 'má', 'vy']):
        return 'sk'
    if any(w in text_lower for w in ['co', 'jak', 'kde', 'kdo', 'je', 'jsem', 'mám', 'máte']):
        return 'cs'
    return 'en'

def is_image_request(text: str) -> bool:
    text_lower = text.lower()
    return any(w in text_lower for w in ['obrázok', 'obrazek', 'image', 'nakresli', 'namaluj', 'generate', 'vytvor'])

def is_video_request(text: str) -> bool:
    text_lower = text.lower()
    return any(w in text_lower for w in ['video', 'animácia', 'animace', 'gif'])

def extract_prompt(text: str) -> str:
    text_lower = text.lower()
    patterns = [
        r'vytvor.*?(.+)',
        r'generate.*?(.+)',
        r'spom.*?(.+)',
        r'nakresli.*?(.+)',
        r'namaluj.*?(.+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return match.group(1).strip()
    return text

async def query_ollama(prompt: str, model: str = "llama3.2") -> str:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False}
        )
        if response.status_code == 200:
            return response.json().get("response", "")
        return f"Error: {response.status_code}"

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "1.2.0",
        "provider": "ollama",
        "sdxl_loaded": False,
        "vram_gb": 0,
    }

@app.post("/query")
async def query(request: QueryRequest):
    try:
        lang = detect_language(request.query)
        
        if is_video_request(request.query):
            return {
                "done": "true",
                "answer": "Video generation je momentálne nedostupné.",
                "agent_name": "TvojTon",
                "success": "false",
                "blocks": {},
                "status": "Disabled",
                "uid": "test-123",
            }
        
        if is_image_request(request.query):
            return {
                "done": "true",
                "answer": "Image generation je momentálne nedostupné.",
                "agent_name": "TvojTon",
                "success": "false",
                "blocks": {},
                "status": "Disabled",
                "uid": "test-123",
            }
        
        answer = await query_ollama(request.query, request.model)
        
        messages = {
            'sk': 'Odpoveď od AI:',
            'cs': 'Odpověď od AI:',
            'en': 'AI Response:',
        }
        
        return {
            "done": "true",
            "answer": f"{messages.get(lang, messages['sk'])} {answer}",
            "agent_name": "TvojTon",
            "success": "true",
            "blocks": {},
            "status": "Ready",
            "uid": "test-123",
            "language": lang,
        }
    except Exception as e:
        return {
            "done": "true",
            "answer": f"Nastala chyba: {str(e)}",
            "agent_name": "TvojTon",
            "success": "false",
            "blocks": {},
            "status": "Error",
            "uid": "test-123",
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7777)
