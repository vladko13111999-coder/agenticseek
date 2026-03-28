import os
import json
import asyncio
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from router import analyze_url, competitor_analysis, format_url_analysis_simple, process_query

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

conversation_state = {"default": {"awaiting_competitor": False, "target_url": ""}}

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
            urls = re.findall(r'https?://[^\s<>"\']+', target_url)
            if urls:
                target = urls[0]
                
                thoughts.append({"step": "Spúšťam analýzu konkurencie", "details": target})
                yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
                
                comp_result, comp_thoughts = await competitor_analysis(target, model)
                thoughts.extend(comp_thoughts)
                yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
                
                for word in comp_result.split():
                    yield "data: " + json.dumps({"type": "chunk", "data": word + " "}) + "\n\n"
                    full_answer += word + " "
                    await asyncio.sleep(0.01)
                
                yield "data: " + json.dumps({"type": "chunk", "data": "\n\n---\nMôžem vám s niečím ďalším pomôcť?Napíšte mi napríklad: 'Napíš SEO blog' alebo 'Priprav email'", "full_answer": ""}) + "\n\n"
                full_answer += "\n\n---\nMôžem vám s niečím ďalším pomôcť?"
                
                conversation_state[session_id] = {"awaiting_competitor": False, "target_url": ""}
        else:
            thoughts.append({"step": "Spracúvam požiadavku", "details": "Odpovedám cez AI..."})
            yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
            
            system_msg = "You are Brand Twin AI assistant for tvojton.online. ALWAYS respond in Slovak."
            messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": query}]
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                payload = {"model": model, "messages": messages, "stream": True}
                async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as response:
                    async for line in response.aiter_lines():
                        if line:
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
        for word in result.split():
            yield "data: " + json.dumps({"type": "chunk", "data": word + " "}) + "\n\n"
            full_answer += word + " "
            await asyncio.sleep(0.01)
    
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
        "version": "4.0.0"
    }

@app.post("/stream-query")
async def stream_query(request: QueryRequest):
    return StreamingResponse(
        generate_response(request.query, "default", request.model),
        media_type="text/event-stream"
    )

@app.post("/analyze-url")
async def analyze_url_endpoint(url: str):
    result, thoughts = await analyze_url(url)
    formatted = format_url_analysis_simple(result)
    return {"result": formatted, "thoughts": thoughts}

@app.post("/competitor-analysis")
async def competitor_analysis_endpoint(url: str):
    result, thoughts = await competitor_analysis(url)
    return {"result": result, "thoughts": thoughts}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
