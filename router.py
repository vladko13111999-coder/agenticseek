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
    system_prompt = """Extract 5-10 most important keywords from the following text. Return ONLY a JSON array of keywords, nothing else.
Example output: ["keyword1", "keyword2", "keyword3"]
Text:"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text[:2000]}
    ]
    
    try:
        result = await ollama_chat(model, messages)
        keywords = json.loads(result)
        return keywords if isinstance(keywords, list) else []
    except:
        return []

async def web_search(query: str, num_results: int = 5) -> List[Dict]:
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                "https://duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            results = []
            if response.status_code == 200:
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

async def analyze_url(url: str, model: str = "gemma3:12b") -> Dict:
    result = {
        "url": url,
        "title": "",
        "meta_description": "",
        "meta_keywords": "",
        "og_tags": {},
        "h1_tags": [],
        "h2_tags": [],
        "links": {"internal": 0, "external": 0},
        "images": 0,
        "products": [],
        "emails": [],
        "phones": [],
        "social_links": {},
        "tech_stack": [],
        "http_status": 0,
        "content_preview": "",
        "keywords": []
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            result["http_status"] = response.status_code
            soup = BeautifulSoup(response.text, "html.parser")
            
            title = soup.find("title")
            result["title"] = title.get_text(strip=True) if title else "No title"
            
            meta_desc = soup.find("meta", attrs={"name": "description"})
            result["meta_description"] = meta_desc.get("content", "") if meta_desc else ""
            
            meta_kw = soup.find("meta", attrs={"name": "keywords"})
            result["meta_keywords"] = meta_kw.get("content", "") if meta_kw else ""
            
            for og_prop in ["og:title", "og:description", "og:image", "og:type", "og:url"]:
                og_tag = soup.find("meta", attrs={"property": og_prop})
                if og_tag:
                    result["og_tags"][og_prop] = og_tag.get("content", "")
            
            result["h1_tags"] = [h.get_text(strip=True) for h in soup.find_all("h1")][:10]
            result["h2_tags"] = [h.get_text(strip=True) for h in soup.find_all("h2")][:15]
            
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
            
            for social in ["facebook", "instagram", "twitter", "linkedin", "youtube"]:
                social_links = soup.find_all("a", href=re.compile(social))
                if social_links:
                    result["social_links"][social] = len(social_links)
            
            product_selectors = [
                {"class": re.compile(r'product|item|card', re.I)},
                {"data": re.compile(r'product|item', re.I)},
                "article",
                {"itemtype": re.compile(r'Product', re.I)}
            ]
            products = []
            for selector in product_selectors:
                items = soup.find_all(class_=selector.get("class")) if "class" in selector else []
                if len(items) > len(products):
                    products = items[:10]
            
            result["products"] = [
                {
                    "name": p.get_text(strip=True)[:100],
                    "price": next((s.get_text(strip=True) for s in p.find_all(class_=re.compile(r'price|cost', re.I)) if s), "N/A")
                }
                for p in products[:5]
            ]
            
            tech_patterns = {
                "WordPress": r'wp-content|wp-includes',
                "Shopify": r'shopifycdn|cdn\.shopify',
                "WooCommerce": r'woocommerce|woo-commerce',
                "React": r'react|react-dom',
                "Vue.js": r'vue\.js|vuejs',
                "Angular": r'angular',
                "jQuery": r'jquery',
                "Bootstrap": r'bootstrap',
                "Tailwind": r'tailwind',
                "Google Analytics": r'google-analytics|gtag',
                "Facebook Pixel": r'facebook.*pixel|fbq',
                "Cloudflare": r'cloudflare',
                "Stripe": r'stripe',
            }
            for tech, pattern in tech_patterns.items():
                if re.search(pattern, response.text):
                    result["tech_stack"].append(tech)
            
            text_content = soup.get_text(separator=" ", strip=True)
            result["content_preview"] = text_content[:500] + "..." if len(text_content) > 500 else text_content
            
            keywords = await extract_keywords(result["title"] + " " + result["meta_description"] + " " + " ".join(result["h1_tags"]), model)
            result["keywords"] = keywords
            
            result["status"] = "success"
            
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result

def format_url_analysis(analysis: Dict) -> str:
    if analysis.get("status") == "error":
        return f"❌ **Chyba pri analýze:** {analysis.get('error', 'Neznáma chyba')}"
    
    md = f"""## 🔍 Analýza webovej stránky

### Základné informácie
| Parameter | Hodnota |
|----------|---------|
| **URL** | {analysis.get('url', 'N/A')} |
| **HTTP Status** | {analysis.get('http_status', 'N/A')} |
| **Titulok** | {analysis.get('title', 'N/A')} |

### Meta tags (SEO)
| Tag | Obsah |
|-----|-------|
| **Meta Description** | {analysis.get('meta_description', 'Chýba')[:200]} |
| **Meta Keywords** | {analysis.get('meta_keywords', 'Chýba')[:200]} |

### Open Graph (Social media)
"""
    
    og = analysis.get("og_tags", {})
    if og:
        md += "| Property | Hodnota |\n|----------|---------|\n"
        for prop, val in og.items():
            md += f"| {prop} | {val[:100]} |\n"
    else:
        md += "*Žiadne OG tagy nenájdené*\n"
    
    md += f"""
### Nadpisy (Heading tags)
- **H1 ({len(analysis.get('h1_tags', []))}):** {', '.join(analysis.get('h1_tags', [])[:5]) or 'Žiadne'}
- **H2 ({len(analysis.get('h2_tags', []))}):** {', '.join(analysis.get('h2_tags', [])[:8]) or 'Žiadne'}

### Kľúčové slová
{', '.join(['' for k in analysis.get('keywords', [])]) or '*Žiadne identifikované*'}

### Obsah
{analysis.get('content_preview', 'N/A')}

### Odkazy a média
- **Interné odkazy:** {analysis.get('links', {}).get('internal', 0)}
- **Externé odkazy:** {analysis.get('links', {}).get('external', 0)}
- **Obrázky:** {analysis.get('images', 0)}

### Kontaktné údaje
"""
    
    emails = analysis.get("emails", [])
    phones = analysis.get("phones", [])
    if emails:
        md += "**Email:** " + ", ".join(emails) + "\n"
    if phones:
        md += "**Telefón:** " + ", ".join(phones) + "\n"
    if not emails and not phones:
        md += "*Žiadne kontaktné údaje nenájdené*\n"
    
    social = analysis.get("social_links", {})
    if social:
        md += "\n### Sociálne siete\n"
        for platform, count in social.items():
            md += f"- **{platform.capitalize()}:** {count} odkazov\n"
    
    products = analysis.get("products", [])
    if products:
        md += "\n### Identifikované produkty\n"
        md += "| Produkt | Cena |\n|---------|------|\n"
        for p in products:
            md += f"| {p['name']} | {p['price']} |\n"
    
    tech = analysis.get("tech_stack", [])
    if tech:
        md += f"\n### Technologický stack\n" + "\n"
        for t in tech:
            md += f"- {t}\n"
    
    return md

async def competitor_analysis(target_url: str, model: str = "gemma3:12b") -> Dict:
    result = {
        "target_url": target_url,
        "competitors": [],
        "comparison": {}
    }
    
    try:
        target_analysis = await analyze_url(target_url, model)
        keywords = target_analysis.get("keywords", [])
        main_keyword = keywords[0] if keywords else ""
        
        result["target_analysis"] = target_analysis
        
        if main_keyword:
            search_results = await web_search(f"konkurent {main_keyword} {target_url}", num_results=5)
        else:
            search_results = await web_search(f"konkurent {target_url}", num_results=5)
        
        competitor_urls = []
        for r in search_results[:4]:
            url = r.get("url", "")
            if url and url != target_url and url.startswith("http"):
                competitor_urls.append(url)
        
        result["competitors"] = competitor_urls
        result["comparison"] = {}
        
        for comp_url in competitor_urls:
            try:
                comp_analysis = await analyze_url(comp_url, model)
                result["comparison"][comp_url] = comp_analysis
            except:
                result["comparison"][comp_url] = {"status": "error", "error": "Failed to analyze"}
        
        result["status"] = "success"
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result

def format_competitor_analysis(analysis: Dict) -> str:
    if analysis.get("status") == "error":
        return f"❌ **Chyba:** {analysis.get('error', 'Neznáma chyba')}"
    
    md = "## 🏢 Analýza konkurencie\n\n"
    
    target = analysis.get("target_analysis", {})
    md += f"### Cieľová stránka: [{target.get('url', 'N/A')}]({target.get('url', '#')})\n"
    md += f"- **Titulok:** {target.get('title', 'N/A')}\n"
    md += f"- **Meta description:** {target.get('meta_description', 'N/A')[:150]}\n"
    md += f"- **H1 nadpisy:** {', '.join(target.get('h1_tags', [])[:3]) or 'Žiadne'}\n"
    md += f"- **Kľúčové slová:** {', '.join(target.get('keywords', [])[:5]) or 'Žiadne'}\n"
    md += f"- **Obrázkov:** {target.get('images', 0)}\n"
    md += f"- **Technológie:** {', '.join(target.get('tech_stack', [])[:5]) or 'Neznáme'}\n\n"
    
    competitors = analysis.get("comparison", {})
    if competitors:
        md += "### 🔍 Nájdení konkurenti\n\n"
        
        md += "| Konkurent | Titulok | Meta Desc | H1 | Obrázky | Tech Stack |\n"
        md += "|-----------|---------|-----------|-----|---------|------------|\n"
        
        for comp_url, comp_data in competitors.items():
            if comp_data.get("status") == "success":
                short_url = comp_url[:40] + "..." if len(comp_url) > 40 else comp_url
                title = comp_data.get("title", "N/A")[:30]
                desc = (comp_data.get("meta_description", "N/A")[:40] or "-")[:40]
                h1_count = str(comp_data.get("h1_count", 0))
                img_count = str(comp_data.get("images", 0))
                tech = ", ".join(comp_data.get("tech_stack", [])[:2]) or "-"
                md += f"| [{short_url}]({comp_url}) | {title} | {desc} | {h1_count} | {img_count} | {tech} |\n"
            else:
                md += f"| {comp_url[:40]} | ❌ Chyba | - | - | - | - |\n"
        
        md += "\n### 📊 Porovnanie silných a slabých stránok\n\n"
        
        target_h1 = len(target.get("h1_tags", []))
        target_img = target.get("images", 0)
        target_tech = len(target.get("tech_stack", []))
        
        for comp_url, comp_data in competitors.items():
            if comp_data.get("status") == "success":
                short_name = comp_url.replace("https://", "").replace("www.", "").split("/")[0][:30]
                comp_h1 = len(comp_data.get("h1_tags", []))
                comp_img = comp_data.get("images", 0)
                comp_tech = len(comp_data.get("tech_stack", []))
                
                md += f"#### {short_name}\n"
                md += "**Silné stránky:** "
                strengths = []
                if comp_h1 > target_h1: strengths.append(f"Viac H1 nadpisov ({comp_h1} vs {target_h1})")
                if comp_img > target_img: strengths.append(f"Viac obrázkov ({comp_img} vs {target_img})")
                if comp_tech > target_tech: strengths.append(f"Pokročilejšia technológia ({comp_tech} technológií)")
                md += ", ".join(strengths) or "Podobná úroveň ako cieľová stránka" + "\n"
                
                md += "**Slabé stránky:** "
                weaknesses = []
                if comp_h1 < target_h1: weaknesses.append(f"Menej H1 nadpisov ({comp_h1} vs {target_h1})")
                if comp_img < target_img: weaknesses.append(f"Menej obrázkov ({comp_img} vs {target_img})")
                if not comp_data.get("meta_description"): weaknesses.append("Chýba meta description")
                if not comp_data.get("og_tags"): weaknesses.append("Chýbajú OG tagy")
                md += ", ".join(weaknesses) or "Žiadne výrazné" + "\n\n"
    
    return md

async def process_query(query: str, model: str = "gemma3:12b") -> Tuple[str, Optional[str], Optional[str]]:
    query_lower = query.lower()
    
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, query)
    
    if 'analyzuj' in query_lower and urls:
        target_url = urls[0]
        analysis = await analyze_url(target_url, model)
        result = format_url_analysis(analysis)
        followup = "Chcete analyzovať aj konkurenciu? Odpovedzte **ÁNO** alebo **NIE**."
        return result, followup, "analyze_competitors"
    
    elif any(word in query_lower for word in ['áno', 'ano', 'yes', 'yea', 'jasne', 'sure']):
        return "__RUN_COMPETITOR_ANALYSIS__", None, None
    
    elif any(word in query_lower for word in ['nie', 'no', 'nope', 'nechcem']):
        return "Rozumiem! Môžem vám s niečím iným pomôcť?\n\nNapríklad:\n- 📝 **Napísať SEO blog** - vytvorím optimalizovaný článok\n- 🔍 **Vyhľadať informácie** - nájdem čokoľvek na webe\n- 📧 **Pripraviť email** - napíšem profesionálny email\n\nStačí povedať!", None, None
    
    else:
        system_msg = "You are Brand Twin AI assistant for tvojton.online. ALWAYS respond in Slovak. Be helpful."
        messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": query}]
        response = await ollama_chat(model, messages)
        return response, None, None
