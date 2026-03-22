import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import httpx

app = FastAPI(title="Brand Twin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tvojton.online",
        "https://www.tvojton.online",
        "http://localhost:3000",
        "http://localhost:5173",
        "https://invision-mistakes-influence-verbal.trycloudflare.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0", "provider": "ollama"}


@app.post("/query")
async def query(request: QueryRequest):
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "gemma3:12b",
                    "prompt": f"Respond as TvojTon, a helpful AI assistant. User: {request.query}",
                    "stream": False,
                },
            )
            result = response.json()
            return {
                "done": "true",
                "answer": result.get("response", "No response"),
                "reasoning": "",
                "agent_name": "TvojTon",
                "success": "true",
                "blocks": {},
                "status": "Ready",
                "uid": "test-123",
            }
    except Exception as e:
        return {
            "done": "true",
            "answer": f"Error: {str(e)}",
            "reasoning": "",
            "agent_name": "TvojTon",
            "success": "false",
            "blocks": {},
            "status": "Error",
            "uid": "test-123",
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7777)
