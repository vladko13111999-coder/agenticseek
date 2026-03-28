import os
import re
import json
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

async def ollama_chat(model: str, messages: List[Dict], stream: bool = False) -> str:
    async with httpx.AsyncClient(timeout=180.0) as client:
        payload = {"model": model, "messages": messages, "stream": stream}
        response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        result = response.json()
        return result.get("message", {}).get("content", "")

async def extract_keywords(text: str, model: str = "gemma3:12b") -> List[str]:
    system_prompt = "Extract 5-10 keywords. Return ONLY JSON array."
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text[:2000]}]
    try:
        result = await ollama_chat(model, messages)
        return json.loads(result) if isinstance(json.loads(result), list) else []
    except:
        return []

async def web_search(query: str, num_results: int = 5) -> List[Dict]:
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get("https://duckduckgo.com/html/", params={"q": query}, headers={"User-Agent": "Mozilla/5.0"})
            results = []
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                for item in soup.select(".result")[:num_results]:
                    title = item.select_one(".result__title")
                    link = item.select_one("a")
                    snippet = item.select_one(".result__snippet")
                    if title and link:
                        results.append({"title": title.get_text(strip=True), "url": link.get("href", ""), "snippet": snippet.get_text(strip=True) if snippet else ""})
            return results
    except:
        return []

async def analyze_url(url: str, model: str = "gemma3:12b") -> Tuple[Dict, List[Dict]]:
    thoughts = []
    result = {"url": url, "title": "", "meta_description": "", "meta_keywords": "", "og_tags": {}, "h1_tags": [], "h2_tags": [], "links": {"internal": 0, "external": 0}, "images": 0, "products": [], "emails": [], "phones": [], "social_links": {}, "tech_stack": [], "http_status": 0, "keywords": []}
    
    try:
        thoughts.append({"step": f"Stahujem: {url}", "details": "Cakam na odpoved..."})
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            result["http_status"] = response.status_code
            soup = BeautifulSoup(response.text, "html.parser")
            thoughts.append({"step": "Parsovanie HTML", "details": f"Status: {response.status_code}"})
            
            title = soup.find("title")
            result["title"] = title.get_text(strip=True) if title else "No title"
            meta_desc = soup.find("meta", attrs={"name": "description"})
            result["meta_description"] = meta_desc.get("content", "") if meta_desc else ""
            meta_kw = soup.find("meta", attrs={"name": "keywords"})
            result["meta_keywords"] = meta_kw.get("content", "") if meta_kw else ""
            
            thoughts.append({"step": "Extrahujem meta tags", "details": "OK"})
            for og_prop in ["og:title", "og:description", "og:image", "og:type"]:
                og_tag = soup.find("meta", attrs={"property": og_prop})
                if og_tag:
                    result["og_tags"][og_prop] = og_tag.get("content", "")
            
            result["h1_tags"] = [h.get_text(strip=True) for h in soup.find_all("h1")][:10]
            result["h2_tags"] = [h.get_text(strip=True) for h in soup.find_all("h2")][:15]
            thoughts.append({"step": "Hladam nadpisy", "details": f"H1: {len(result['h1_tags'])}, H2: {len(result['h2_tags'])}"})
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith("http"):
                    if url in href or href.startswith("/"):
                        result["links"]["internal"] += 1
                    else:
                        result["links"]["external"] += 1
            
            result["images"] = len(soup.find_all("img"))
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', response.text)
            result["emails"] = list(set(emails))[:5]
            phones = re.findall(r'[\+]?[0-9\s\-\(\)]{7,}', response.text)
            result["phones"] = list(set([p.strip() for p in phones if len(p.strip()) > 8]))[:5]
            
            thoughts.append({"step": "Hladam kontakty", "details": f"Email: {len(result['emails'])}, Tel: {len(result['phones'])}"})
            
            for social in ["facebook", "instagram", "twitter", "linkedin", "youtube"]:
                social_links = soup.find_all("a", href=re.compile(social))
                if social_links:
                    result["social_links"][social] = len(social_links)
            
            tech_patterns = {"WordPress": r'wp-content|wp-includes', "Shopify": r'shopifycdn|cdn\.shopify', "React": r'react|react-dom', "jQuery": r'jquery', "Bootstrap": r'bootstrap', "Tailwind": r'tailwind', "Google Analytics": r'google-analytics|gtag', "Cloudflare": r'cloudflare'}
            for tech, pattern in tech_patterns.items():
                if re.search(pattern, response.text):
                    result["tech_stack"].append(tech)
            
            thoughts.append({"step": "Detekujem tech stack", "details": ", ".join(result['tech_stack'][:3]) or "Ziadne"})
            
            keywords = await extract_keywords(result["title"] + " " + result["meta_description"] + " " + " ".join(result["h1_tags"]), model)
            result["keywords"] = keywords
            thoughts.append({"step": "Analýza dokoncena", "details": url})
            result["status"] = "success"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        thoughts.append({"step": "Chyba", "details": str(e)})
    
    return result, thoughts

def format_url_analysis(analysis: Dict) -> str:
    if analysis.get("status") == "error":
        return f"<div style='background:#ffebee;padding:15px;border-radius:8px;border-left:4px solid #ea4335;'>Chyba: {analysis.get('error', 'Neznáma')}</div>"
    
    status_color = '#34a853' if analysis.get('http_status')==200 else '#ea4335'
    url_short = analysis.get('url', 'N/A')[:60] + ('...' if len(analysis.get('url',''))>60 else '')
    
    og_html = ""
    for prop, val in analysis.get("og_tags", {}).items():
        og_html += f"<p style='margin:5px 0;'><strong>{prop}:</strong> {val[:100]}</p>"
    if not og_html:
        og_html = "<p>Ziadne OG tagy</p>"
    
    h1_html = "".join([f"<li>{h}</li>" for h in analysis.get('h1_tags', [])[:5]]) or '<li>Ziadne</li>'
    h2_html = "".join([f"<li>{h}</li>" for h in analysis.get('h2_tags', [])[:10]]) or '<li>Ziadne</li>'
    
    keywords_html = "".join([f"<span style='background:#e8f0fe;padding:4px 8px;border-radius:4px;margin:3px;display:inline-block;'>{k}</span>" for k in analysis.get('keywords', [])]) or '<span>Ziadne</span>'
    
    tech_html = "".join([f"<span style='background:#f0f0f0;padding:3px 8px;border-radius:3px;margin:2px;display:inline-block;'>{t}</span>" for t in analysis.get('tech_stack', [])]) or '<span>Ziadne</span>'
    
    social_html = ""
    for platform, count in analysis.get("social_links", {}).items():
        emoji = {"facebook": "👤", "instagram": "📷", "twitter": "🐦", "linkedin": "💼", "youtube": "▶️"}.get(platform, "🔗")
        social_html += f"<p>{emoji} <strong>{platform}:</strong> {count}</p>"
    
    emails = analysis.get("emails", [])
    phones = analysis.get("phones", [])
    contact_html = ""
    if emails:
        contact_html += f"<p><strong>Email:</strong> {', '.join(emails)}</p>"
    if phones:
        contact_html += f"<p><strong>Tel:</strong> {', '.join(phones)}</p>"
    if not contact_html:
        contact_html = "<p>Ziadne kontakty</p>"
    
    return f"""<div style='background:#f8f9fa;border-radius:12px;padding:20px;margin:10px 0;border-left:4px solid #4285f4;'>
<h2 style='color:#1a1a1a;margin-top:0;'>🔍 Analýza webovej stránky</h2>

<table style='width:100%;border-collapse:collapse;background:#fff;border-radius:8px;'>
<tr style='background:#e8f0fe;'><td style='padding:10px;font-weight:bold;width:140px;'>🌐 URL</td><td style='padding:10px;'><a href='{analysis.get('url', 'N/A')}'>{url_short}</a></td></tr>
<tr><td style='padding:10px;font-weight:bold;'>📊 Status</td><td style='padding:10px;color:{status_color};font-weight:bold;'>{analysis.get('http_status', 'N/A')}</td></tr>
<tr style='background:#f8f9fa;'><td style='padding:10px;font-weight:bold;'>📝 Titulok</td><td style='padding:10px;'>{analysis.get('title', 'N/A')}</td></tr>
</table>

<details open style='margin-top:15px;'>
<summary style='cursor:pointer;font-weight:bold;color:#1a1a1a;padding:10px;background:#fff3cd;border-radius:6px;'>🏷️ SEO Meta tags</summary>
<div style='background:#fff;padding:10px;'>
<p style='margin:5px 0;'><strong>Description:</strong> {analysis.get('meta_description', 'Chýba')[:200] or 'Chýba'}</p>
<p style='margin:5px 0;'><strong>Keywords:</strong> {analysis.get('meta_keywords', 'Chýba')[:200] or 'Chýba'}</p>
</div>
</details>

<details style='margin-top:10px;'>
<summary style='cursor:pointer;font-weight:bold;color:#1a1a1a;padding:10px;background:#e8f5e9;border-radius:6px;'>📱 Open Graph</summary>
<div style='background:#fff;padding:10px;border-radius:0 0 6px 6px;'>{og_html}</div>
</details>

<details style='margin-top:10px;'>
<summary style='cursor:pointer;font-weight:bold;color:#1a1a1a;padding:10px;background:#e3f2fd;border-radius:6px;'>📌 Nadpisy</summary>
<div style='background:#fff;padding:10px;'>
<p><strong>H1 ({len(analysis.get('h1_tags', []))}):</strong></p><ul>{h1_html}</ul>
<p style='margin-top:10px;'><strong>H2 ({len(analysis.get('h2_tags', []))}):</strong></p><ul>{h2_html}</ul>
</div>
</details>

<details style='margin-top:10px;'>
<summary style='cursor:pointer;font-weight:bold;color:#1a1a1a;padding:10px;background:#f3e5f5;border-radius:6px;'>🔑 Kľúčové slová</summary>
<div style='background:#fff;padding:10px;'>{keywords_html}</div>
</details>

<details style='margin-top:10px;'>
<summary style='cursor:pointer;font-weight:bold;color:#1a1a1a;padding:10px;background:#fff3e0;border-radius:6px;'>🔗 Odkazy</summary>
<div style='background:#fff;padding:10px;'>
<p>📪 Interné: <strong>{analysis.get('links', {}).get('internal', 0)}</strong></p>
<p>🔗 Externé: <strong>{analysis.get('links', {}).get('external', 0)}</strong></p>
<p>🖼️ Obrázky: <strong>{analysis.get('images', 0)}</strong></p>
</div>
</details>

<details style='margin-top:10px;'>
<summary style='cursor:pointer;font-weight:bold;color:#1a1a1a;padding:10px;background:#e0f7fa;border-radius:6px;'>📧 Kontakty</summary>
<div style='background:#fff;padding:10px;'>{contact_html}</div>
</details>

<details style='margin-top:10px;'>
<summary style='cursor:pointer;font-weight:bold;color:#1a1a1a;padding:10px;background:#fce4ec;border-radius:6px;'>📱 Sociálne siete</summary>
<div style='background:#fff;padding:10px;'>{social_html or '<p>Ziadne</p>'}</div>
</details>

<details style='margin-top:10px;'>
<summary style='cursor:pointer;font-weight:bold;color:#1a1a1a;padding:10px;background:#f5f5f5;border-radius:6px;'>⚙️ Tech stack</summary>
<div style='background:#fff;padding:10px;'>{tech_html}</div>
</details>
</div>"""

async def competitor_analysis(target_url: str, model: str = "gemma3:12b") -> Tuple[Dict, List[Dict]]:
    thoughts = []
    result = {"target_url": target_url, "competitors": [], "comparison": {}}
    
    try:
        thoughts.append({"step": "Analyzujem cielovu stranku", "details": target_url})
        target_analysis, _ = await analyze_url(target_url, model)
        keywords = target_analysis.get("keywords", [])
        main_keyword = keywords[0] if keywords else ""
        result["target_analysis"] = target_analysis
        
        thoughts.append({"step": "Hladam konkurentov", "details": main_keyword or "URL"})
        search_results = await web_search(f"konkurent {main_keyword}" if main_keyword else f"konkurent {target_url}", num_results=5)
        
        competitor_urls = []
        for r in search_results[:4]:
            url = r.get("url", "")
            if url and url != target_url and url.startswith("http") and "google" not in url:
                competitor_urls.append(url)
        
        result["competitors"] = competitor_urls
        for comp_url in competitor_urls:
            thoughts.append({"step": f"Analyzujem: {comp_url[:40]}", "details": "Scraping..."})
            try:
                comp_analysis, _ = await analyze_url(comp_url, model)
                result["comparison"][comp_url] = comp_analysis
            except:
                result["comparison"][comp_url] = {"status": "error", "error": "Failed"}
        
        thoughts.append({"step": "Hotovo", "details": f"Pocet: {len(competitor_urls)}"})
        result["status"] = "success"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        thoughts.append({"step": "Chyba", "details": str(e)})
    
    return result, thoughts

def format_competitor_analysis(analysis: Dict) -> str:
    if analysis.get("status") == "error":
        return f"<div style='background:#ffebee;padding:15px;border-radius:8px;'>Chyba: {analysis.get('error')}</div>"
    
    target = analysis.get("target_analysis", {})
    keywords_html = " ".join([f"<span style='background:#e8f0fe;padding:2px 6px;border-radius:3px;'>{k}</span>" for k in target.get('keywords', [])[:5]]) or '<span>Ziadne</span>'
    
    md = f"""<div style='background:#e8f5e9;border-radius:12px;padding:20px;margin:10px 0;border-left:4px solid #34a853;'>
<h2 style='color:#1a1a1a;margin-top:0;'>🏢 Analýza konkurencie</h2>

<div style='background:#fff;padding:15px;border-radius:8px;margin-bottom:15px;'>
<h3 style='margin-top:0;color:#4285f4;'>🎯 Cieľová stránka</h3>
<p><strong>URL:</strong> <a href='{target.get('url', 'N/A')}'>{target.get('url', 'N/A')}</a></p>
<p><strong>Titulok:</strong> {target.get('title', 'N/A')}</p>
<p><strong>Kľúčové slová:</strong> {keywords_html}</p>
</div>"""
    
    competitors = analysis.get("comparison", {})
    if competitors:
        md += """<h3>🔍 Porovnanie</h3>
<table style='width:100%;border-collapse:collapse;background:#fff;border-radius:8px;'>
<thead style='background:#1a1a1a;color:#fff;'><tr><th style='padding:12px;'>Konkurent</th><th style='padding:12px;'>Titulok</th><th style='padding:12px;text-align:center;'>H1</th><th style='padding:12px;text-align:center;'>IMG</th></tr></thead>
<tbody>"""
        
        target_h1 = len(target.get("h1_tags", []))
        target_img = target.get("images", 0)
        
        for comp_url, comp_data in competitors.items():
            if comp_data.get("status") == "success":
                short_url = comp_url.replace("https://","").replace("www.","").split("/")[0][:25]
                h1_count = len(comp_data.get("h1_tags", []))
                h1_color = "#34a853" if h1_count > target_h1 else "#ea4335" if h1_count < target_h1 else "#1a1a1a"
                md += f"""<tr>
<td style='padding:10px;'><a href='{comp_url}'>{short_url}</a></td>
<td style='padding:10px;'>{comp_data.get('title', 'N/A')[:35]}</td>
<td style='padding:10px;text-align:center;color:{h1_color};font-weight:bold;'>{h1_count}</td>
<td style='padding:10px;text-align:center;'>{comp_data.get('images', 0)}</td>
</tr>"""
        
        md += "</tbody></table></div>"
    
    return md

async def process_query(query: str, model: str = "gemma3:12b") -> Tuple[str, Optional[str], Optional[str], List[Dict]]:
    query_lower = query.lower()
    urls = re.findall(r'https?://[^s]+', query)
    
    if 'analyzuj' in query_lower and urls:
        target_url = urls[0]
        thoughts = [{"step": "Detekovaná požiadavka na analýzu URL", "details": target_url}, {"step": "Spúšťam analýzu", "details": "Scraping, SEO..."}]
        analysis, analysis_thoughts = await analyze_url(target_url, model)
        thoughts.extend(analysis_thoughts)
        result = format_url_analysis(analysis)
        thoughts.append({"step": "Analýza dokončená", "details": "Zobrazujem výsledky"})
        followup = "<div style='background:#fff3cd;padding:15px;border-radius:8px;margin-top:15px;border-left:4px solid #f0ad4e;'><p style='margin:0;font-weight:bold;'>❓ Chcete analyzovať aj konkurenciu?</p><p style='margin:5px 0 0 0;color:#666;'>Odpovedzte <strong>ÁNO</strong> alebo <strong>NIE</strong></p></div>"
        return result, followup, "awaiting_competitor", thoughts
    
    elif any(word in query_lower for word in ['áno', 'ano', 'yes', 'yea', 'jasne']):
        return "__RUN_COMPETITOR_ANALYSIS__", None, None, [{"step": "Používateľ súhlasil", "details": "Spúšťam analýzu konkurencie"}]
    
    elif any(word in query_lower for word in ['nie', 'no', 'nope', 'nechcem']):
        return "<div style='background:#e8f5e9;padding:15px;border-radius:8px;margin-top:10px;'><p style='margin:0;'>✅ Rozumiem! Možnosti:</p><ul><li>📝 Napísať SEO blog</li><li>🔍 Vyhľadať info</li><li>📧 Pripraviť email</li></ul></div>", None, None, [{"step": "Používateľ odmietol", "details": "Ponúkam ďalšie možnosti"}]
    
    else:
        thoughts = [{"step": "Spracúvam požiadavku", "details": "Odpovedám cez AI..."}]
        system_msg = "You are Brand Twin AI assistant for tvojton.online. ALWAYS respond in Slovak."
        messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": query}]
        response = await ollama_chat(model, messages)
        return response, None, None, thoughts
