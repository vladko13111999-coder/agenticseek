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
        thoughts.append({"step": f"Stahujem: {url}", "details": "..."})
        
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
        system_prompt = f"Extraahuj 5-7 hlavnych klicovych slov. Odpovedz LEN JSON pole. Text: {text_for_keywords[:500]}"
        try:
            resp = await ollama_chat(model, [{"role": "user", "content": system_prompt}])
            result["keywords"] = json.loads(resp)
        except:
            result["keywords"] = []
        
        thoughts.append({"step": "Hotovo", "details": url})
        result["status"] = "success"
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        thoughts.append({"step": "Chyba", "details": str(e)})
    
    return result, thoughts

def format_url_analysis_simple(analysis: Dict) -> str:
    if analysis.get("status") == "error":
        return f"CHYBA pri analýze: {analysis.get('error', 'Neznáma chyba')}"
    
    good, improve, recommendations = [], [], []
    
    if analysis.get("http_status") == 200:
        good.append("Web je online a dostupný")
    if analysis.get("title"):
        good.append(f"Má titulok: '{analysis['title'][:40]}'")
    if analysis.get("meta_description") and len(analysis.get("meta_description", "")) > 100:
        good.append("Má kvalitný meta popis")
    if analysis.get("h1_count", 0) >= 1:
        good.append(f"Má {analysis['h1_count']} H1 nadpisov")
    if analysis.get("tech_stack"):
        good.append(f"Tech: {', '.join(analysis['tech_stack'][:2])}")
    
    if not analysis.get("meta_description"):
        improve.append("CHÝBA meta description - veľmi dôležité pre SEO")
    elif len(analysis.get("meta_description", "")) < 80:
        improve.append(f"Meta popis je krátky ({len(analysis.get('meta_description', ''))} znakov)")
    if analysis.get("h1_count", 0) == 0:
        improve.append("CHÝBA H1 nadpis - kľúčový pre SEO")
    if analysis.get("h2_count", 0) < 3:
        improve.append(f"Málo H2 nadpisov ({analysis['h2_count']})")
    if analysis.get("images", 0) < 3:
        improve.append(f"Málo obrázkov ({analysis['images']})")
    
    if not analysis.get("meta_description"):
        recommendations.append("Pridať meta description 150-160 znakov")
    if analysis.get("h1_count", 0) == 0:
        recommendations.append("Pridať H1 nadpis s kľúčovým slovom")
    if analysis.get("h2_count", 0) < 3:
        recommendations.append("Pridať viac H2 nadpisov")
    recommendations.append("Pravidelne pridávať nový obsah (blog)")
    
    # Build clear response
    resp = f"ANALYZA WEBU: {analysis.get('url', 'N/A')}\n"
    resp += "=" * 40 + "\n\n"
    
    if good:
        resp += "CO JE DOBRE:\n"
        resp += "-" * 20 + "\n"
        for item in good:
            resp += f"  + {item}\n"
        resp += "\n"
    
    if improve:
        resp += "CO TREBA ZLEPSIT:\n"
        resp += "-" * 20 + "\n"
        for item in improve:
            resp += f"  ! {item}\n"
        resp += "\n"
    
    if recommendations:
        resp += "ODPORUCANIA:\n"
        resp += "-" * 20 + "\n"
        for i, item in enumerate(recommendations, 1):
            resp += f"  {i}. {item}\n"
        resp += "\n"
    
    resp += "=" * 40 + "\n"
    resp += "\n"
    resp += "CHCETE ABY SOM ANALYZOVAL VASICH KONKURENTOV?\n"
    resp += "Odpovedzte: ANO alebo NIE\n"
    
    return resp

async def competitor_analysis(url: str, model: str = "gemma3:12b") -> Tuple[str, List[Dict]]:
    thoughts = []
    thoughts.append({"step": "Analyzujem cielovu stranku", "details": url})
    target_data, _ = await analyze_url(url, model)
    
    if target_data.get("status") != "success":
        return f"CHYBA: Nepodarilo sa analyzovat {url}", thoughts
    
    keywords = target_data.get("keywords", [])
    main_keyword = keywords[0] if keywords else ""
    domain_name = url.replace("https://", "").replace("www.", "").split("/")[0]
    
    thoughts.append({"step": "Hladam konkurentov", "details": main_keyword or domain_name})
    
    search_queries = []
    if main_keyword:
        search_queries.append(f"{main_keyword} eshop Slovensko")
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
    
    # Build clear response
    resp = f"ANALYZA KONKURENCIE: {domain_name}\n"
    resp += "=" * 40 + "\n\n"
    resp += f"VASA STRANKA: {target_data.get('title', 'N/A')}\n"
    resp += f"KLICOVE SLOVA: {', '.join(keywords[:5]) if keywords else 'Neuvedene'}\n\n"
    resp += "NAJDENI KONKURENTI:\n"
    resp += "-" * 20 + "\n\n"
    
    target_h1 = target_data.get("h1_count", 0)
    
    for i, comp in enumerate(competitor_data, 1):
        comp_url = comp["url"]
        comp_data = comp["data"]
        short_name = comp_url.replace("https://", "").replace("www.", "").split("/")[0][:30]
        
        resp += f"{i}. {short_name}\n"
        resp += f"   Titulok: {comp_data.get('title', 'N/A')[:40]}\n"
        
        meta = comp_data.get('meta_description', '')
        if meta:
            resp += f"   Meta: {meta[:50]}...\n"
        
        comp_h1 = comp_data.get('h1_count', 0)
        if comp_h1 > target_h1:
            resp += f"   => Ma viac H1 nadpisov ({comp_h1} vs vasich {target_h1})\n"
        
        resp += "\n"
    
    resp += "=" * 40 + "\n\n"
    resp += "ODPORUCANIA NA ZAKLADE KONKURENCIE:\n"
    resp += "-" * 20 + "\n"
    
    best_h1 = max([c['data'].get('h1_count', 0) for c in competitor_data], default=0)
    if best_h1 > target_h1:
        resp += f"  + Konkurenti maju viac H1 nadpisov - pridajte viac strukturovaneho obsahu\n"
    
    if keywords:
        resp += f"  + Vase klicove slova ({', '.join(keywords[:3])}) su dobre - pokracujte\n"
    
    resp += "\n"
    resp += "=" * 40 + "\n"
    resp += "\n"
    resp += "CHCETE ABY SOM NAPISAL SEO BLOG?\n"
    resp += "Odpovedzte: ANO alebo NIE\n"
    
    return resp, thoughts

async def process_query(query: str, model: str = "gemma3:12b") -> Tuple[str, Optional[str], Optional[str], List[Dict]]:
    query_lower = query.lower()
    urls = re.findall(r'https?://[^\s<>"\']+', query)
    
    if any(word in query_lower for word in ['analyzuj', 'analyza', 'analyze', 'analyzuj web', 'analyzuj stranku', 'analyzuj url']) and urls:
        target_url = urls[0]
        thoughts = [{"step": "Detekovana poziadavka", "details": target_url}]
        analysis, analysis_thoughts = await analyze_url(target_url, model)
        thoughts.extend(analysis_thoughts)
        return format_url_analysis_simple(analysis), "", "awaiting_competitor", thoughts
    
    elif any(word in query_lower for word in ['konkurent', 'konkurentov']):
        if urls:
            thoughts = [{"step": "Analyza konkurencie", "details": urls[0]}]
            result, comp_thoughts = await competitor_analysis(urls[0], model)
            return result, "", "done", comp_thoughts
        return "Potrebujem URL adresu. Napiste: 'analyzuj konkurentov https://...'", "", "done", []
    
    elif any(word in query_lower for word in ['áno', 'ano', 'yes', 'chcem', 'jasne', 'joj']):
        return "__RUN_COMPETITOR_ANALYSIS__", None, None, [{"step": "Suhlas s analyzou konkurencie", "details": "..."}]
    
    elif any(word in query_lower for word in ['nie', 'no', 'nope', 'nechcem', 'dakujem']):
        return """ROZUMIEM!

CO DALSIE MOZEM UROBIT:
  1. Analyzovat dalsi web
  2. Napisat SEO blog
  3. Pripravit email
  4. Vyhladat informacie

Staci napisat co chcete!\n""", None, None, [{"step": "Odmietol ponuku konkurencie", "details": "..."}]
    
    else:
        thoughts = [{"step": "Spracuvam poziadavku", "details": "..."}]
        system_msg = "You are Brand Twin AI assistant. Always respond in Slovak. Keep responses short and helpful."
        messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": query}]
        response = await ollama_chat(model, messages)
        return response, None, None, thoughts
