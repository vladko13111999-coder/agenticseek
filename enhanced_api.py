import os
import json
import asyncio
import httpx
import websockets
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI(title="Brand Twin AI - OpenClaw Enhanced")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OPENCLAW_URL = os.getenv("OPENCLAW_URL", "ws://localhost:18789")

class Message(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    query: str
    history: Optional[List[Message]] = []
    model: Optional[str] = "gemma3:12b"

class WebSearchRequest(BaseModel):
    query: str
    num_results: int = 5

class AnalyzeUrlRequest(BaseModel):
    url: str

class CompetitorRequest(BaseModel):
    urls: List[str]

class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str

async def ollama_chat(model: str, messages: List[Dict], stream: bool = True):
    async with httpx.AsyncClient(timeout=180.0) as client:
        payload = {"model": model, "messages": messages, "stream": stream}
        async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    yield line + "\n"

async def web_search(query: str, num_results: int = 5) -> List[Dict]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            results = []
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")
                for item in soup.select(".result")[:num_results]:
                    title = item.select_one(".result__title")
                    link = item.select_one("a")
                    snippet = item.select_one(".result__snippet")
                    if title and link:
                        results.append({
                            "title": title.get_text(strip=True),
                            "url": link.get("href", ""),
                            "snippet": snippet.get_text(strip=True) if snippet else ""
                        })
            return results
    except Exception as e:
        return [{"error": str(e)}]

async def analyze_url(url: str) -> Dict:
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            title = soup.find("title")
            meta_desc = soup.find("meta", attrs={"name": "description"})
            meta_keywords = soup.find("meta", attrs={"name": "keywords"})
            og_title = soup.find("meta", attrs={"property": "og:title"})
            og_image = soup.find("meta", attrs={"property": "og:image"})
            
            h1_tags = [h.get_text(strip=True) for h in soup.find_all("h1")]
            h2_tags = [h.get_text(strip=True) for h in soup.find_all("h2")]
            
            canonical = soup.find("link", attrs={"rel": "canonical"})
            
            return {
                "status": "success",
                "url": url,
                "title": title.get_text(strip=True) if title else "No title",
                "meta_description": meta_desc.get("content", "") if meta_desc else "",
                "meta_keywords": meta_keywords.get("content", "") if meta_keywords else "",
                "og_title": og_title.get("content", "") if og_title else "",
                "og_image": og_image.get("content", "") if og_image else "",
                "h1_count": len(h1_tags),
                "h1_tags": h1_tags[:5],
                "h2_tags": h2_tags[:10],
                "canonical": canonical.get("href", "") if canonical else url,
                "http_status": response.status_code
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def generate_response_with_openclaw(query: str, model: str = "gemma3:12b"):
    thoughts = []
    full_answer = ""
    
    if any(keyword in query.lower() for keyword in ["analyzuj", "search", "vyhľadaj", "url", "stránku", "porovnaj"]):
        thoughts.append({"step": "Detekovaná požiadavka na analýzu/webove vyhľadávanie", "details": "Používam OpenClaw nástroje"})
        yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
        
        if "url" in query.lower() or "stránku" in query.lower():
            import re
            urls = re.findall(r'https?://[^\s]+', query)
            for url in urls[:1]:
                thoughts.append({"step": "Analýza URL: " + url, "details": "Získavanie dát..."})
                yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
                
                analysis = await analyze_url(url)
                thoughts.append({"step": "Analýza dokončená", "details": "Status: " + str(analysis.get("status", "unknown"))})
                yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
                
                header = "**Analýza stránky " + url + "**\n\n"
                yield "data: " + json.dumps({"type": "chunk", "data": header}) + "\n\n"
                full_answer += header
                
                if analysis.get("status") == "success":
                    summary = """📊 **Výsledky analýzy:**

**Titulok:** """ + analysis.get("title", "N/A") + """
**Meta description:** """ + analysis.get("meta_description", "N/A") + """
**Počet H1:** """ + str(analysis.get("h1_count", 0)) + """
**H1 nadpisy:** """ + ", ".join(analysis.get("h1_tags", [])[:3]) or "Žiadne" + """

**OG Title:** """ + analysis.get("og_title", "N/A") + """
**Canonical:** """ + analysis.get("canonical", "N/A") + """
**HTTP Status:** """ + str(analysis.get("http_status", "N/A")) + """"
"""
                    for word in summary.split():
                        yield "data: " + json.dumps({"type": "chunk", "data": word + " "}) + "\n\n"
                        full_answer += word + " "
                        await asyncio.sleep(0.02)
                else:
                    error_msg = "❌ Chyba pri analýze: " + str(analysis.get("error", "Neznáma chyba"))
                    yield "data: " + json.dumps({"type": "chunk", "data": error_msg}) + "\n\n"
                    full_answer += error_msg
        
        elif any(word in query.lower() for word in ["vyhľadaj", "search", "nájdi"]):
            search_query = query.lower()
            for w in ["vyhľadaj", "search", "nájdi"]:
                search_query = search_query.replace(w, "").strip()
            
            thoughts.append({"step": "Vyhľadávanie: " + search_query, "details": "Hľadám na webe..."})
            yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
            
            results = await web_search(search_query)
            thoughts.append({"step": "Vyhľadávanie dokončené", "details": "Nájdených " + str(len(results)) + " výsledkov"})
            yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
            
            header = "🔍 **Výsledky vyhľadávania pre: " + search_query + "**\n\n"
            yield "data: " + json.dumps({"type": "chunk", "data": header}) + "\n\n"
            full_answer += header
            
            for i, r in enumerate(results[:5], 1):
                if isinstance(r, dict) and "title" in r:
                    line = str(i) + ". **" + r["title"] + "**\n   " + r.get("url", "") + "\n   " + r.get("snippet", "") + "\n\n"
                    for word in line.split():
                        yield "data: " + json.dumps({"type": "chunk", "data": word + " "}) + "\n\n"
                        full_answer += word + " "
                        await asyncio.sleep(0.02)
    else:
        thoughts.append({"step": "Spracúvam požiadavku cez Ollama", "details": "Model: " + model})
        yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
        
        system_msg = "You are Brand Twin AI assistant for tvojton.online. ALWAYS respond in Slovak language only. Be friendly and helpful."
        
        messages = [{"role": "system", "content": system_msg}]
        messages.append({"role": "user", "content": query})
        
        async for line in ollama_chat(model, messages, stream=True):
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
        "version": "2.0.0"
    }

@app.post("/stream-query")
async def stream_query(request: QueryRequest):
    return StreamingResponse(
        generate_response_with_openclaw(request.query, request.model),
        media_type="text/event-stream"
    )

@app.post("/web-search")
async def web_search_endpoint(req: WebSearchRequest):
    results = await web_search(req.query, req.num_results)
    return {"results": results}

@app.post("/analyze-url")
async def analyze_url_endpoint(req: AnalyzeUrlRequest):
    result = await analyze_url(req.url)
    return result

@app.post("/competitor-analysis")
async def competitor_analysis(req: CompetitorRequest):
    results = []
    for url in req.urls:
        analysis = await analyze_url(url)
        results.append(analysis)
    return {"results": results}

@app.post("/send-email")
async def send_email(req: SendEmailRequest):
    return {"status": "simulated", "message": f"Email by bol poslaný na {req.to}", "subject": req.subject}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
