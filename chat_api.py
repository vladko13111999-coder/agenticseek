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

conversation_state = {"default": {"awaiting_competitor": False, "target_url": ""}}

async def ollama_stream(model: str, messages: List[dict]):
    async with httpx.AsyncClient(timeout=180.0) as client:
        payload = {"model": model, "messages": messages, "stream": True}
        async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    yield line + "\n"

def get_session_id(history: List[Message]) -> str:
    return "default"

async def generate_response(query: str, session_id: str = "default", model: str = "gemma3:12b"):
    thoughts = []
    full_answer = ""
    
    thoughts.append({"step": "Prijal som požiadavku", "details": query[:50]})
    yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
    
    result, followup, action, new_thoughts = await process_query(query, model)
    thoughts.extend(new_thoughts)
    
    yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
    
    if action == "awaiting_competitor":
        conversation_state[session_id] = {"awaiting_competitor": True, "target_url": query}
        
        yield "data: " + json.dumps({"type": "chunk", "data": result}) + "\n\n"
        full_answer += result
        
        yield "data: " + json.dumps({"type": "chunk", "data": followup}) + "\n\n"
        full_answer += followup
        
    elif result == "__RUN_COMPETITOR_ANALYSIS__":
        state = conversation_state.get(session_id, {})
        
        if state.get("awaiting_competitor"):
            target_url = state.get("target_url", "")
            
            import re
            urls = re.findall(r'https?://[^\s<>"\']+', target_url)
            if urls:
                target = urls[0]
                
                thoughts.append({"step": "Spúšťam analýzu konkurencie", "details": target})
                yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
                
                yield "data: " + json.dumps({"type": "chunk", "data": "<div style='background:#e3f2fd;padding:15px;border-radius:8px;margin:10px 0;'><p style='margin:0;'><strong>🔍 Hľadám konkurentov...</strong></p></div>"}) + "\n\n"
                full_answer += "<p>🔍 Hľadám konkurentov...</p>"
                
                analysis, analysis_thoughts = await competitor_analysis(target, model)
                thoughts.extend(analysis_thoughts)
                yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
                
                comp_result = format_competitor_analysis(analysis)
                
                yield "data: " + json.dumps({"type": "chunk", "data": comp_result}) + "\n\n"
                full_answer += comp_result
                
                conversation_state[session_id] = {"awaiting_competitor": False, "target_url": ""}
                
                offer = """<div style="background:#f8f9fa;padding:15px;border-radius:8px;margin-top:15px;">
<p style="margin:0 0 10px 0;font-weight:bold;">📝 Môžem vám ešte pomôcť:</p>
<ul style="margin:0;padding-left:20px;">
<li>📝 <strong>Napísať SEO blog</strong></li>
<li>🔍 <strong>Vyhľadať informácie</strong></li>
<li>📧 <strong>Pripraviť email</strong></li>
</ul>
</div>"""
                
                yield "data: " + json.dumps({"type": "chunk", "data": offer}) + "\n\n"
                full_answer += offer
        else:
            thoughts.append({"step": "Spracúvam požiadavku", "details": "Odpovedám cez AI..."})
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
    
    else:
        thoughts.append({"step": "Odpoveď pripravená", "details": "Zobrazujem"})
        yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
        
        yield "data: " + json.dumps({"type": "chunk", "data": result}) + "\n\n"
        full_answer += result
    
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
        "version": "3.1.0"
    }

@app.post("/stream-query")
async def stream_query(request: QueryRequest):
    return StreamingResponse(
        generate_response(request.query, get_session_id(request.history or []), request.model),
        media_type="text/event-stream"
    )

@app.post("/analyze-url")
async def analyze_url_endpoint(req: AnalyzeUrlRequest):
    result, thoughts = await analyze_url(req.url)
    formatted = format_url_analysis(result)
    return {"result": result, "formatted": formatted, "thoughts": thoughts}

@app.post("/competitor-analysis")
async def competitor_analysis_endpoint(req: CompetitorRequest):
    result, thoughts = await competitor_analysis(req.target_url)
    formatted = format_competitor_analysis(result)
    return {"result": result, "formatted": formatted, "thoughts": thoughts}

@app.post("/web-search")
async def web_search_endpoint(query: str, num_results: int = 5):
    results = await web_search(query, num_results)
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
