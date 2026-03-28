import os
import json
import asyncio
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from router import (
    analyze_url, competitor_analysis, 
    format_url_analysis, format_competitor_analysis,
    process_query, web_search
)

app = FastAPI(title="Brand Twin AI - OpenClaw Enhanced")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

class Message(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    query: str
    history: Optional[List[Message]] = []
    model: Optional[str] = "gemma3:12b"

class AnalyzeUrlRequest(BaseModel):
    url: str

class CompetitorRequest(BaseModel):
    target_url: str

conversation_state = {}

async def ollama_stream(model: str, messages: List[dict]):
    async with httpx.AsyncClient(timeout=180.0) as client:
        payload = {"model": model, "messages": messages, "stream": True}
        async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    yield line + "\n"

async def generate_response(query: str, session_id: str = "default", model: str = "gemma3:12b"):
    thoughts = []
    full_answer = ""
    
    thoughts.append({"step": "Analýza požiadavky", "details": "Spracúvam..."})
    yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
    
    result, followup, action = await process_query(query, model)
    
    if action == "analyze_competitors":
        conversation_state[session_id] = {"awaiting_competitor": True, "target_url": query}
        thoughts.append({"step": "Analýza dokončená", "details": "Čakám na odpoveď o konkurencii"})
        yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
        
        for word in result.split():
            yield "data: " + json.dumps({"type": "chunk", "data": word + " "}) + "\n\n"
            full_answer += word + " "
            await asyncio.sleep(0.01)
        
        yield "data: " + json.dumps({"type": "chunk", "data": "\n\n" + followup + "\n"}) + "\n\n"
        full_answer += "\n\n" + followup
        
    elif result == "__RUN_COMPETITOR_ANALYSIS__":
        state = conversation_state.get(session_id, {})
        
        if state.get("awaiting_competitor"):
            target_url = state.get("target_url", "")
            
            import re
            urls = re.findall(r'https?://[^\s]+', target_url)
            if urls:
                target = urls[0]
                
                thoughts.append({"step": "Spúšťam analýzu konkurencie", "details": "Hľadám konkurentov..."})
                yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
                
                yield "data: " + json.dumps({"type": "chunk", "data": "🔍 **Analyzujem konkurenciu pre:** " + target + "\n\n"}) + "\n\n"
                full_answer += "🔍 **Analyzujem konkurenciu pre:** " + target + "\n\n"
                
                analysis = await competitor_analysis(target, model)
                comp_result = format_competitor_analysis(analysis)
                
                for word in comp_result.split():
                    yield "data: " + json.dumps({"type": "chunk", "data": word + " "}) + "\n\n"
                    full_answer += word + " "
                    await asyncio.sleep(0.01)
                
                conversation_state[session_id] = {}
                
                yield "data: " + json.dumps({"type": "chunk", "data": "\n\n---\n\n📝 **Môžem vám ešte pomôcť?**\n- Napísať SEO blog\n- Pripraviť email\n- Vyhľadať informácie\n"}) + "\n\n"
                full_answer += "\n\n---\n\n📝 **Môžem vám ešte pomôcť?**\n- Napísať SEO blog\n- Pripraviť email\n- Vyhľadať informácie\n"
        else:
            thoughts.append({"step": "Spracúvam požiadavku", "details": "Odpovedám cez Ollama..."})
            yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
            
            system_msg = "You are Brand Twin AI assistant for tvojton.online. ALWAYS respond in Slovak."
            messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": query}]
            
            async for line in ollama_stream(model, messages):
                try:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        chunk = data["message"]["content"]
                        yield "data: " + json.dumps({"type": "chunk", "data": chunk}) + "\n\n"
                        full_answer += chunk
                    if data.get("done"):
                        break
                except:
                    pass
    
    elif action == None and result:
        thoughts.append({"step": "Odpoveď pripravená", "details": "Hotovo"})
        yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
        
        for word in result.split():
            yield "data: " + json.dumps({"type": "chunk", "data": word + " "}) + "\n\n"
            full_answer += word + " "
            await asyncio.sleep(0.01)
    
    else:
        thoughts.append({"step": "Spracúvam požiadavku", "details": "Odpovedám cez Ollama..."})
        yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
        
        system_msg = "You are Brand Twin AI assistant for tvojton.online. ALWAYS respond in Slovak. Be helpful and friendly."
        messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": query}]
        
        async for line in ollama_stream(model, messages):
            try:
                data = json.loads(line)
                if "message" in data and "content" in data["message"]:
                    chunk = data["message"]["content"]
                    yield "data: " + json.dumps({"type": "chunk", "data": chunk}) + "\n\n"
                    full_answer += chunk
                if data.get("done"):
                    break
            except:
                pass
    
    yield "data: " + json.dumps({"type": "done", "full_answer": full_answer, "thoughts": thoughts}) + "\n\n"

@app.get("/health")
async def health():
    ollama_ok = False
    openclaw_ok = False
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            ollama_ok = resp.status_code == 200
    except:
        pass
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://localhost:18789/health")
            openclaw_ok = resp.status_code == 200
    except:
        pass
    
    return {
        "status": "healthy" if ollama_ok else "degraded",
        "ollama": "online" if ollama_ok else "offline",
        "openclaw": "online" if openclaw_ok else "offline",
        "version": "3.0.0"
    }

@app.post("/stream-query")
async def stream_query(request: QueryRequest):
    session_id = request.history[-1].content[:50] if request.history else "default"
    return StreamingResponse(
        generate_response(request.query, session_id, request.model),
        media_type="text/event-stream"
    )

@app.post("/analyze-url")
async def analyze_url_endpoint(req: AnalyzeUrlRequest):
    result = await analyze_url(req.url)
    formatted = format_url_analysis(result)
    return {"result": result, "formatted": formatted}

@app.post("/competitor-analysis")
async def competitor_analysis_endpoint(req: CompetitorRequest):
    result = await competitor_analysis(req.target_url)
    formatted = format_competitor_analysis(result)
    return {"result": result, "formatted": formatted}

@app.post("/web-search")
async def web_search_endpoint(query: str, num_results: int = 5):
    results = await web_search(query, num_results)
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
