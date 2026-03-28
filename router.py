import os
import re
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

async def ollama_chat(model: str, messages: List[Dict], stream: bool = False) -> str:
    import httpx
    async with httpx.AsyncClient(timeout=180.0) as client:
        payload = {"model": model, "messages": messages, "stream": stream}
        response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        result = response.json()
        return result.get("message", {}).get("content", "")

async def google_search(query: str, num_results: int = 5) -> List[Dict]:
    try:
        from googlesearch import search
        results = []
        for url in search(query, num_results=num_results, lang='sk'):
            if url and url.startswith('http') and 'google' not in url:
                results.append({"url": url})
        return results
    except:
        return []

async def analyze_url(url: str, model: str = "gemma3:12b") -> Tuple[Dict, List[Dict]]:
    thoughts = []
    result = {"url": url, "title": "", "meta_description": "", "h1_count": 0, "h1_tags": [],
              "h2_count": 0, "images": 0, "tech_stack": [], "keywords": [], "links": {}}
    
    try:
        thoughts.append({"step": f"Stahujem: {url}", "details": "Cakam na odpoved..."})
        
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=30)
        except:
            http_url = url.replace("https://", "http://")
            response = requests.get(http_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        
        result["http_status"] = response.status_code
        soup = BeautifulSoup(response.text, "html.parser")
        
        title = soup.find("title")
        result["title"] = title.get_text(strip=True) if title else ""
        
        meta_desc = soup.find("meta", attrs={"name": "description"})
        result["meta_description"] = meta_desc.get("content", "") if meta_desc else ""
        
        h1_tags = soup.find_all("h1")
        result["h1_count"] = len(h1_tags)
        result["h1_tags"] = [h.get_text(strip=True) for h in h1_tags[:5]]
        
        result["h2_count"] = len(soup.find_all("h2"))
        result["images"] = len(soup.find_all("img"))
        
        internal_links = 0
        external_links = 0
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith("http"):
                if url in href:
                    internal_links += 1
                else:
                    external_links += 1
        
        result["links"] = {"internal": internal_links, "external": external_links}
        
        tech_patterns = {
            "WordPress": r'wp-content|wp-includes',
            "Shopify": r'shopifycdn|cdn\.shopify',
            "WooCommerce": r'woocommerce',
            "React": r'react|react-dom',
            "jQuery": r'jquery',
            "Google Analytics": r'google-analytics|gtag',
            "Cloudflare": r'cloudflare',
        }
        for tech, pattern in tech_patterns.items():
            if re.search(pattern, response.text):
                result["tech_stack"].append(tech)
        
        text_for_keywords = result["title"] + " " + result["meta_description"] + " " + " ".join(result["h1_tags"])
        system_prompt = f"Jsi SEO specialista. Extrahuj 5-7 hlavnych klicovych slov. Odpovez POUZE JSON pole. Text: {text_for_keywords[:500]}"
        try:
            resp = await ollama_chat(model, [{"role": "user", "content": system_prompt}])
            result["keywords"] = json.loads(resp)
        except:
            result["keywords"] = []
        
        thoughts.append({"step": "Analyza dokoncena", "details": url})
        result["status"] = "success"
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        thoughts.append({"step": "Chyba", "details": str(e)})
    
    return result, thoughts

def format_url_analysis_simple(analysis: Dict) -> str:
    if analysis.get("status") == "error":
        return f"❌ Chyba: {analysis.get('error', 'Neznáma')}"
    
    good, improve, recommendations = [], [], []
    
    if analysis.get("http_status") == 200:
        good.append("Web je online")
    if analysis.get("title"):
        good.append(f"Titulok: '{analysis['title'][:50]}...'")
    if analysis.get("meta_description") and len(analysis.get("meta_description", "")) > 100:
        good.append("Ma kvalitny meta popis")
    if analysis.get("h1_count", 0) >= 1:
        good.append(f"Ma {analysis['h1_count']} H1 nadpisov")
    if analysis.get("tech_stack"):
        good.append(f"Tech: {', '.join(analysis['tech_stack'][:2])}")
    
    if not analysis.get("meta_description"):
        improve.append("Chyba meta description")
    elif len(analysis.get("meta_description", "")) < 80:
        improve.append(f"Meta popis je kratky ({len(analysis.get('meta_description', ''))} znakov)")
    if analysis.get("h1_count", 0) == 0:
        improve.append("Chyba H1 nadpis")
    if analysis.get("h2_count", 0) < 3:
        improve.append(f"Malo H2 nadpisov ({analysis['h2_count']})")
    if analysis.get("images", 0) < 3:
        improve.append(f"Malo obrazkov ({analysis['images']})")
    
    if not analysis.get("meta_description"):
        recommendations.append("Pridajte meta description 150-160 znakov")
    if analysis.get("h1_count", 0) == 0:
        recommendations.append("Pridajte H1 nadpis s klicovym slovom")
    if analysis.get("h2_count", 0) < 3:
        recommendations.append("Rozsirte obsah o H2 nadpisy")
    recommendations.append("Pridajte pravidelne novy obsah (blog)")
    
    resp = f"📊 **Analyza: {analysis.get('url', 'N/A')}**\n\n"
    
    if good:
        resp += "**✅ Co je dobre:**\n" + "\n".join([f"• {x}" for x in good]) + "\n\n"
    if improve:
        resp += "**⚠️ Co treba zlepsit:**\n" + "\n".join([f"• {x}" for x in improve]) + "\n\n"
    if recommendations:
        resp += "**🚀 Odporucania:**\n" + "\n".join([f"{i}. {x}" for i, x in enumerate(recommendations, 1)]) + "\n\n"
    
    resp += "---\nChcete analyzovat konkurentov? Odpovedzte **ANO** alebo **NIE**."
    return resp

async def competitor_analysis(url: str, model: str = "gemma3:12b") -> Tuple[str, List[Dict]]:
    thoughts = []
    thoughts.append({"step": "Analyzujem cielovu stranku", "details": url})
    target_data, _ = await analyze_url(url, model)
    
    if target_data.get("status") != "success":
        return f"❌ Nepodarilo sa analyzovat {url}", thoughts
    
    keywords = target_data.get("keywords", [])
    main_keyword = keywords[0] if keywords else ""
    domain_name = url.replace("https://", "").replace("www.", "").split("/")[0]
    
    thoughts.append({"step": "Hladam konkurentov", "details": main_keyword or domain_name})
    
    search_queries = []
    if main_keyword:
        search_queries.append(f"{main_keyword} eshop")
    search_queries.append(f"konkurent {domain_name}")
    
    all_competitors = []
    for query in search_queries[:2]:
        thoughts.append({"step": f"Google: {query}", "details": "..."})
        results = await google_search(query, num_results=5)
        for r in results:
            if r.get("url") and r["url"] not in [c["url"] for c in all_competitors]:
                if url not in r["url"]:
                    all_competitors.append(r)
        if len(all_competitors) >= 5:
            break
    
    competitor_data = []
    for comp in all_competitors[:5]:
        comp_url = comp["url"]
        thoughts.append({"step": f"Analyzujem: {comp_url[:30]}", "details": "..."})
        data, _ = await analyze_url(comp_url, model)
        if data.get("status") == "success":
            competitor_data.append({"url": comp_url, "data": data})
    
    thoughts.append({"step": "Hotovo", "details": f"{len(competitor_data)} konkurentov"})
    
    if not competitor_data:
        return f"Nenasiel som konkurentov pre {url}", thoughts
    
    resp = f"🏢 **Analyza konkurencie: {domain_name}**\n\n"
    resp += f"**Vasa stranka:** {target_data.get('title', 'N/A')}\n"
    resp += f"**Klicova slova:** {', '.join(keywords[:5]) if keywords else 'Neuvedene'}\n\n"
    resp += "**Najdeni konkurenti:**\n\n"
    
    target_h1 = target_data.get("h1_count", 0)
    
    for i, comp in enumerate(competitor_data, 1):
        comp_url = comp["url"]
        comp_data = comp["data"]
        short_name = comp_url.replace("https://", "").replace("www.", "").split("/")[0][:30]
        
        resp += f"**{i}. {short_name}**\n"
        resp += f"   Titulok: {comp_data.get('title', 'N/A')[:40]}\n"
        
        meta = comp_data.get('meta_description', '')
        if meta:
            resp += f"   Meta: {meta[:60]}...\n"
        
        comp_h1 = comp_data.get('h1_count', 0)
        if comp_h1 > target_h1:
            resp += f"   💡 Viacej H1 nadpisov ({comp_h1} vs vasich {target_h1})\n"
        resp += "\n"
    
    resp += "---\n\n**🎯 Odporucania:**\n"
    
    best_h1 = max([c['data'].get('h1_count', 0) for c in competitor_data], default=0)
    if best_h1 > target_h1:
        resp += f"• Konkurenti maju viac H1 nadpisov - odporucam pridat viac\n"
    
    resp += "\n---\nChcete napisat SEO blog? Odpovedzte **ANO** alebo **NIE**."
    return resp, thoughts

async def process_query(query: str, model: str = "gemma3:12b") -> Tuple[str, Optional[str], Optional[str], List[Dict]]:
    query_lower = query.lower()
    urls = re.findall(r'https?://[^\s<>"\']+', query)
    
    if any(word in query_lower for word in ['analyzuj', 'analyza', 'analyze', 'analyzuj web', 'analyzuj stranku']) and urls:
        target_url = urls[0]
        thoughts = [{"step": "Detekovana poziadavka", "details": target_url}, {"step": "Spustam analyzu", "details": "..."}]
        analysis, analysis_thoughts = await analyze_url(target_url, model)
        thoughts.extend(analysis_thoughts)
        return format_url_analysis_simple(analysis), "", "awaiting_competitor", thoughts
    
    elif any(word in query_lower for word in ['konkurent', 'competitor']):
        if urls:
            thoughts = [{"step": "Spustam analyzu konkurencie", "details": urls[0]}]
            result, comp_thoughts = await competitor_analysis(urls[0], model)
            return result, "", "done", comp_thoughts
        return "Potrebujem URL. Napiste: 'analyzuj konkurentov https://...'", "", "done", []
    
    elif any(word in query_lower for word in ['áno', 'ano', 'yes', 'chcem', 'jasne']):
        return "__RUN_COMPETITOR_ANALYSIS__", None, None, [{"step": "Suhlas", "details": "Spustam konkurentov"}]
    
    elif any(word in query_lower for word in ['nie', 'no', 'nope', 'nechcem', 'dakujem']):
        return """✅ Rozumiem! Co dalsie?

• 🔍 Analyzovat dalsi web
• 📝 Napisat SEO blog
• 📧 Pripravit email""", None, None, [{"step": "Odmietol", "details": "Ponukam dalsie"}]
    
    else:
        thoughts = [{"step": "Spracuvam", "details": "Odpovedam..."}]
        system_msg = "You are Brand Twin AI assistant. Respond in Slovak."
        messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": query}]
        response = await ollama_chat(model, messages)
        return response, None, None, thoughts
import os
import json
import asyncio
import httpx
import re
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

conversation_state = {"default": {"awaiting_competitor": False, "target_url": "", "last_action": ""}}

async def generate_response(query: str, session_id: str = "default", model: str = "gemma3:12b"):
    global conversation_state
    
    thoughts = []
    full_answer = ""
    
    thoughts.append({"step": "Prijal som poziadavku", "details": query[:50]})
    yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
    
    result, followup, action, new_thoughts = await process_query(query, model)
    thoughts.extend(new_thoughts)
    
    yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
    
    if action == "awaiting_competitor":
        # Save state - waiting for competitor analysis decision
        import re
        urls = re.findall(r'https?://[^\s<>"\']+', query)
        if urls:
            conversation_state[session_id] = {"awaiting_competitor": True, "target_url": query, "last_action": "analyze"}
        
        # Stream result word by word
        words = result.split()
        for word in words:
            yield "data: " + json.dumps({"type": "chunk", "data": word + " "}) + "\n\n"
            full_answer += word + " "
            await asyncio.sleep(0.01)
        
        yield "data: " + json.dumps({"type": "chunk", "data": "\n\n"}) + "\n\n"
        full_answer += "\n\n"
        
    elif result == "__RUN_COMPETITOR_ANALYSIS__":
        state = conversation_state.get(session_id, {})
        
        if state.get("awaiting_competitor"):
            target_url = state.get("target_url", "")
            urls = re.findall(r'https?://[^\s<>"\']+', target_url)
            
            if urls:
                target = urls[0]
                
                thoughts.append({"step": "Spustam analyzu konkurencie", "details": target})
                yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
                
                comp_result, comp_thoughts = await competitor_analysis(target, model)
                thoughts.extend(comp_thoughts)
                yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
                
                # Stream result word by word
                words = comp_result.split()
                for word in words:
                    yield "data: " + json.dumps({"type": "chunk", "data": word + " "}) + "\n\n"
                    full_answer += word + " "
                    await asyncio.sleep(0.01)
                
                conversation_state[session_id] = {"awaiting_competitor": False, "target_url": "", "last_action": "competitor_done"}
            else:
                thoughts.append({"step": "Chyba", "details": "Nenasiel som URL"})
                yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
                error_msg = "❌ Nenasiel som URL adresu. Skuste to znova."
                yield "data: " + json.dumps({"type": "chunk", "data": error_msg}) + "\n\n"
                full_answer += error_msg
        else:
            thoughts.append({"step": "Spracuvam", "details": "Odpovedam cez AI..."})
            yield "data: " + json.dumps({"type": "thoughts", "data": thoughts}) + "\n\n"
            
            system_msg = "You are Brand Twin AI assistant. Respond in Slovak."
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
    
    elif action == "done":
        # Stream result
        words = result.split()
        for word in words:
            yield "data: " + json.dumps({"type": "chunk", "data": word + " "}) + "\n\n"
            full_answer += word + " "
            await asyncio.sleep(0.01)
        
        conversation_state[session_id] = {"awaiting_competitor": False, "target_url": "", "last_action": "done"}
    
    else:
        # Stream result
        words = result.split()
        for word in words:
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
        "version": "5.0.0"
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
