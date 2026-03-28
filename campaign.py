import os
import json
import re
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

ONECOM_API_KEY = os.getenv("ONECOM_API_KEY", "")
ONECOM_SENDER = os.getenv("ONECOM_SENDER", "Tvojton")

INFOBIP_API_KEY = os.getenv("INFOBIP_API_KEY", "")
INFOBIP_BASE_URL = os.getenv("INFOBIP_BASE_URL", "https://api.infobip.com")
INFOBIP_SENDER = os.getenv("INFOBIP_SENDER", "TvojtonAI")

CAMPAIGNS_DIR = "/root/agenticseek/campaigns"

os.makedirs(CAMPAIGNS_DIR, exist_ok=True)

class CampaignStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    EXHAUSTED = "exhausted"

class LeadStatus(Enum):
    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    CONVERTED = "converted"
    NOT_INTERESTED = "not_interested"

@dataclass
class Lead:
    url: str
    email: str = ""
    phone: str = ""
    name: str = ""
    company: str = ""
    title: str = ""
    status: str = "new"
    contacted_at: str = ""
    responded_at: str = ""
    method: str = ""
    notes: str = ""
    personalizations: Dict = field(default_factory=dict)

@dataclass
class Campaign:
    id: str
    target_segment: str
    monthly_limit: int
    daily_limit: int = 10
    status: str = "pending"
    leads_contacted: int = 0
    leads_interested: int = 0
    created_at: str = ""
    last_run: str = ""
    telegram_enabled: bool = True
    calls_enabled: bool = False
    email_template: str = ""
    sms_template: str = ""
    call_script: str = ""
    admin_telegram: str = ""

def get_campaign_file(campaign_id: str) -> str:
    return f"{CAMPAIGNS_DIR}/{campaign_id}.json"

def load_campaign(campaign_id: str) -> Optional[Campaign]:
    filepath = get_campaign_file(campaign_id)
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
            return Campaign(**data)
    return None

def save_campaign(campaign: Campaign):
    filepath = get_campaign_file(campaign.id)
    with open(filepath, "w") as f:
        json.dump(asdict(campaign), f, indent=2, default=str)

def load_leads(campaign_id: str) -> List[Lead]:
    filepath = f"{CAMPAIGNS_DIR}/{campaign_id}_leads.json"
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
            return [Lead(**l) for l in data]
    return []

def save_leads(campaign_id: str, leads: List[Lead]):
    filepath = f"{CAMPAIGNS_DIR}/{campaign_id}_leads.json"
    with open(filepath, "w") as f:
        json.dump([asdict(l) for l in leads], f, indent=2, default=str)

async def ollama_chat(model: str, messages: List[Dict], stream: bool = False) -> str:
    import httpx
    async with httpx.AsyncClient(timeout=180.0) as client:
        payload = {"model": model, "messages": messages, "stream": stream}
        response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        result = response.json()
        return result.get("message", {}).get("content", "")

def send_telegram(message: str, bot_token: str = None, chat_id: str = None):
    token = bot_token or TELEGRAM_BOT_TOKEN
    chat = chat_id or TELEGRAM_CHAT_ID
    
    if not token or not chat:
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(url, json={
            "chat_id": chat,
            "text": message,
            "parse_mode": "HTML"
        })
        return response.status_code == 200
    except:
        return False

async def google_search(query: str, num_results: int = 10) -> List[str]:
    try:
        from googlesearch import search
        results = []
        for url in search(query, num_results=num_results, lang='sk'):
            if url and isinstance(url, str) and url.startswith('http') and 'google' not in url.lower():
                results.append(url)
        return results
    except:
        return []

def extract_contact_info(url: str) -> Dict:
    info = {"email": "", "phone": "", "name": "", "company": ""}
    
    try:
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }, verify=False, timeout=15)
        
        text = response.text
        soup = BeautifulSoup(text, "html.parser")
        
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        for email in emails:
            if 'noreply' not in email.lower() and 'no-reply' not in email.lower():
                info["email"] = email
                break
        
        phone_pattern = r'[\+]?[0-9]{1,3}[-\.\s]?\(?[0-9]{1,4}\)?[-\.\s]?[0-9]{1,4}[-\.\s]?[0-9]{1,9}'
        phones = re.findall(phone_pattern, text)
        for phone in phones:
            clean_phone = re.sub(r'[^\d\+]', '', phone)
            if len(clean_phone) >= 9:
                info["phone"] = clean_phone
                break
        
        title = soup.find("title")
        if title:
            info["company"] = title.get_text(strip=True)[:60]
        
    except:
        pass
    
    return info

def analyze_website_for_personalization(url: str) -> Dict:
    analysis = {
        "title": "",
        "description": "",
        "products": [],
        "tone": "profesionálny"
    }
    
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        title = soup.find("title")
        analysis["title"] = title.get_text(strip=True) if title else ""
        
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            analysis["description"] = meta_desc.get("content", "")[:200]
        
        h1_tags = soup.find_all("h1")
        for h1 in h1_tags[:3]:
            text = h1.get_text(strip=True)
            if len(text) > 5 and len(text) < 100:
                analysis["products"].append(text)
        
    except:
        pass
    
    return analysis

async def generate_personalized_email(lead: Lead, campaign: Campaign, website_analysis: Dict) -> str:
    prompt = f"""Napíš krátky, osobný predajný email v slovenčine.

Oslovovaná firma: {lead.company}
Web: {lead.url}
Produkty/Služby: {', '.join(website_analysis.get('products', [])[:3]) or 'neurčené'}

Moja ponuka: {campaign.target_segment}

Požiadavky:
- Max 150 slov
- Osobné oslovenie (meno ak je: {lead.name})
- Zameraj sa na hodnotu pre zákazníka
- Konkrétny benefit (ukážka, konzultácia)
- Výzva na odpoveď "ÁNO"
- Krátky podpis

FORMÁT:
PREDMET: ...
TEXT: ..."""

    try:
        return await ollama_chat("gemma3:12b", [{"role": "user", "content": prompt}])
    except:
        return f"""PREDMET: Krátka ponuka pre {lead.company or 'vašu firmu'}

Dobrý deň{', ' + lead.name if lead.name else ''},

oslovujem vás s ponukou, ktorá by mohla pomôcť vášmu podnikaniu.

Môžeme sa dohodnúť na 15-minútovom hovore tento týždeň?

Odpovedzte <b>ÁNO</b> a dohodneme sa na čase.

S pozdravom,
Tvojton AI"""

async def generate_call_script(lead: Lead, campaign: Campaign) -> str:
    return f"""Dobrý deň, hovorím z Tvojton.

Volám ohľadom ponuky pre {lead.company}. Mám pripravenú krátku ukážku našich služieb.

Môžeme sa dohodnúť na 15-minútovom hovore alebo stretnutí tento týždeň?

Ďakujem za váš čas."""

def send_email_simulation(to_email: str, subject: str, body: str) -> bool:
    print(f"[EMAIL] To: {to_email}\nSubject: {subject}")
    return True

def send_sms_simulation(to_phone: str, message: str) -> bool:
    print(f"[SMS] To: {to_phone}\nMessage: {message[:100]}")
    return True

def send_call_simulation(to_phone: str, script: str) -> Dict:
    print(f"[CALL] To: {to_phone}")
    return {"status": "simulated", "duration": 45, "result": "interested"}

def make_call_infobip(phone: str, script: str) -> Dict:
    if not INFOBIP_API_KEY:
        return {"error": "INFOBIP_API_KEY not configured"}
    
    url = f"{INFOBIP_BASE_URL}/tts/3/single/advanced"
    
    headers = {
        "Authorization": f"App {INFOBIP_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "from": INFOBIP_SENDER,
        "to": phone,
        "language": "sk",
        "voice": {"name": " Petra"},
        "text": script,
        "rate": "8000",
        "paragraphSpeed": "-5",
        "record": True
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "initiated",
                "call_id": data.get(" CallsId", ""),
                "message_id": data.get("messageId", "")
            }
        else:
            return {"error": f"HTTP {response.status_code}", "details": response.text}
    except Exception as e:
        return {"error": str(e)}

def make_call_oneai(phone: str, script: str) -> Dict:
    if not ONECOM_API_KEY:
        return {"error": "ONECOM_API_KEY not configured"}
    
    url = "https://api.1com.cloud/v1/calls/text-to-speech"
    
    headers = {
        "Authorization": f"Bearer {ONECOM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "to": phone,
        "from": ONECOM_SENDER,
        "text": script,
        "language": "sk-SK",
        "voice": "女",
        "webhook_url": ""
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code in [200, 201, 202]:
            data = response.json()
            return {
                "status": "initiated",
                "call_id": data.get("call_id", data.get("id", "")),
                "duration_estimate": data.get("duration", 60)
            }
        else:
            return {"error": f"HTTP {response.status_code}", "details": response.text}
    except Exception as e:
        return {"error": str(e)}

def make_call(phone: str, script: str) -> Dict:
    if not phone or len(phone) < 9:
        return {"error": "Invalid phone number"}
    
    phone = re.sub(r'[^\d\+]', '', phone)
    if not phone.startswith('+'):
        phone = '+421' + phone.lstrip('0')
    
    if INFOBIP_API_KEY:
        result = make_call_infobip(phone, script)
        if "error" not in result:
            return result
    
    if ONECOM_API_KEY:
        result = make_call_oneai(phone, script)
        if "error" not in result:
            return result
    
    return {"error": "No call provider configured", "simulated": True, "phone": phone, "script": script}

def send_sms_infobip(phone: str, message: str) -> Dict:
    if not INFOBIP_API_KEY:
        return {"error": "INFOBIP_API_KEY not configured"}
    
    url = f"{INFOBIP_BASE_URL}/sms/2/text/single"
    
    headers = {
        "Authorization": f"App {INFOBIP_API_KEY}",
        "Content-Type": "application/json"
    }
    
    phone = re.sub(r'[^\d\+]', '', phone)
    if not phone.startswith('+'):
        phone = '+421' + phone.lstrip('0')
    
    payload = {
        "from": INFOBIP_SENDER,
        "to": phone,
        "text": message
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return {"status": "sent", "message_id": data.get("messages", [{}])[0].get("messageId", "")}
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def send_sms_onecom(phone: str, message: str) -> Dict:
    if not ONECOM_API_KEY:
        return {"error": "ONECOM_API_KEY not configured"}
    
    url = "https://api.1com.cloud/v1/sms"
    
    headers = {
        "Authorization": f"Bearer {ONECOM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    phone = re.sub(r'[^\d\+]', '', phone)
    if not phone.startswith('+'):
        phone = '+421' + phone.lstrip('0')
    
    payload = {
        "to": phone,
        "from": ONECOM_SENDER,
        "text": message
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code in [200, 201, 202]:
            return {"status": "sent", "message_id": response.json().get("id", "")}
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def send_sms(phone: str, message: str) -> Dict:
    if not phone or len(phone) < 9:
        return {"error": "Invalid phone number"}
    
    if INFOBIP_API_KEY:
        result = send_sms_infobip(phone, message)
        if "error" not in result:
            return result
    
    if ONECOM_API_KEY:
        result = send_sms_onecom(phone, message)
        if "error" not in result:
            return result
    
    print(f"[SMS] To: {phone}\nMessage: {message}")
    return {"status": "simulated", "phone": phone}

async def run_campaign_step(campaign_id: str) -> Dict:
    campaign = load_campaign(campaign_id)
    if not campaign:
        return {"error": "Campaign not found"}
    
    leads = load_leads(campaign_id)
    new_leads = [l for l in leads if l.status == LeadStatus.NEW.value]
    
    if not new_leads:
        return {"action": "no_leads", "message": "Nemám nových leadov."}
    
    today = datetime.now().date()
    contacted_today = len([l for l in leads if l.contacted_at and 
                          datetime.fromisoformat(l.contacted_at).date() == today])
    
    if contacted_today >= campaign.daily_limit:
        return {"action": "daily_limit", "message": f"Denný limit ({campaign.daily_limit}) dosiahnutý."}
    
    if campaign.leads_contacted >= campaign.monthly_limit:
        campaign.status = CampaignStatus.EXHAUSTED.value
        save_campaign(campaign)
        send_telegram(f"⚠️ KAMPAŇ VYČERPANÁ\n{ campaign.target_segment}\nOslovených: {campaign.leads_contacted}")
        return {"action": "exhausted", "message": "Mesačný limit dosiahnutý."}
    
    lead = new_leads[0]
    
    website_analysis = analyze_website_for_personalization(lead.url)
    contact_info = extract_contact_info(lead.url)
    
    if contact_info["email"] and not lead.email:
        lead.email = contact_info["email"]
    if contact_info["phone"] and not lead.phone:
        lead.phone = contact_info["phone"]
    if contact_info["company"]:
        lead.company = contact_info["company"]
    
    lead.personalizations = website_analysis
    
    email_content = await generate_personalized_email(lead, campaign, website_analysis)
    
    lines = email_content.split('\n')
    subject = ""
    body_lines = []
    in_body = False
    
    for line in lines:
        if 'PREDMET' in line.upper() or 'SUBJECT' in line.upper():
            subject = line.split(':', 1)[1].strip()
            in_body = True
        elif in_body:
            body_lines.append(line)
    
    body = '\n'.join(body_lines).strip() or email_content
    
    if lead.email:
        send_email_simulation(lead.email, subject, body)
        lead.status = LeadStatus.CONTACTED.value
        lead.contacted_at = datetime.now().isoformat()
        lead.method = "email"
        campaign.leads_contacted += 1
    elif lead.phone and campaign.calls_enabled:
        call_script = await generate_call_script(lead, campaign)
        send_call_simulation(lead.phone, call_script)
        lead.status = LeadStatus.CONTACTED.value
        lead.contacted_at = datetime.now().isoformat()
        lead.method = "call"
        campaign.leads_contacted += 1
    
    campaign.last_run = datetime.now().isoformat()
    save_campaign(campaign)
    
    for i, l in enumerate(leads):
        if l.url == lead.url:
            leads[i] = lead
            break
    save_leads(campaign_id, leads)
    
    return {
        "action": "contacted",
        "lead": asdict(lead),
        "contacted_today": contacted_today + 1,
        "remaining": campaign.monthly_limit - campaign.leads_contacted
    }

async def check_lead_response(campaign_id: str, lead_url: str, response_text: str) -> Dict:
    campaign = load_campaign(campaign_id)
    if not campaign:
        return {"error": "Campaign not found"}
    
    leads = load_leads(campaign_id)
    lead = next((l for l in leads if l.url == lead_url), None)
    
    if not lead:
        return {"error": "Lead not found"}
    
    response_lower = response_text.lower().strip()
    
    if response_lower in ["áno", "ano", "yes"]:
        lead.status = LeadStatus.INTERESTED.value
        lead.responded_at = datetime.now().isoformat()
        campaign.leads_interested += 1
        save_campaign(campaign)
        
        for i, l in enumerate(leads):
            if l.url == lead_url:
                leads[i] = lead
                break
        save_leads(campaign_id, leads)
        
        send_telegram(f"""🎯 ZÁUJEM!
Firma: {lead.company}
Email: {lead.email}
Tel: {lead.phone}
Celkovo zainteresovaných: {campaign.leads_interested}""")
        
        return {"action": "interested", "message": "Skvelé! Pošlem podrobnosti."}
    
    elif any(w in response_lower for w in ["nie", "no", "nechcem", "ďakujem"]):
        lead.status = LeadStatus.NOT_INTERESTED.value
        for i, l in enumerate(leads):
            if l.url == lead_url:
                leads[i] = lead
                break
        save_leads(campaign_id, leads)
        return {"action": "not_interested", "message": "Rozumiem. Ďakujem."}
    
    return {"action": "needs_clarification", "message": "Odpovedzte ÁNO ak máte záujem."}

async def start_campaign(target_segment: str, monthly_limit: int = 50, daily_limit: int = 10) -> Tuple[str, Campaign]:
    campaign_id = f"camp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    campaign = Campaign(
        id=campaign_id,
        target_segment=target_segment,
        monthly_limit=monthly_limit,
        daily_limit=daily_limit,
        status=CampaignStatus.RUNNING.value,
        created_at=datetime.now().isoformat()
    )
    
    save_campaign(campaign)
    
    response = f"""🚀 KAMPAŇ VYTVORENÁ!

ID: {campaign_id}
Cieľ: {target_segment}
Limit: {monthly_limit}/mesiac
Denný limit: {daily_limit}

Začnem hľadať zákazníkov..."""
    
    return response, campaign

async def search_and_import_leads(campaign_id: str, query: str = "") -> List[Lead]:
    campaign = load_campaign(campaign_id)
    if not campaign:
        return []
    
    search_query = query or f"{campaign.target_segment} eshop Slovensko"
    urls = await google_search(search_query, num_results=20)
    
    leads = []
    for url in urls[:15]:
        lead = Lead(url=url)
        try:
            info = extract_contact_info(url)
            lead.email = info.get("email", "")
            lead.phone = info.get("phone", "")
            lead.company = info.get("company", "")
        except:
            pass
        leads.append(lead)
    
    existing_leads = load_leads(campaign_id)
    existing_urls = [l.url for l in existing_leads]
    new_leads = [l for l in leads if l.url not in existing_urls]
    
    save_leads(campaign_id, existing_leads + new_leads)
    return new_leads

def get_campaign_status(campaign_id: str) -> Dict:
    campaign = load_campaign(campaign_id)
    if not campaign:
        return {"error": "Campaign not found"}
    
    leads = load_leads(campaign_id)
    
    return {
        "id": campaign.id,
        "target": campaign.target_segment,
        "status": campaign.status,
        "limit": campaign.monthly_limit,
        "contacted": campaign.leads_contacted,
        "interested": campaign.leads_interested,
        "total_leads": len(leads),
        "new_leads": len([l for l in leads if l.status == LeadStatus.NEW.value]),
        "remaining": campaign.monthly_limit - campaign.leads_contacted
    }

def list_campaigns() -> List[Dict]:
    campaigns = []
    if os.path.exists(CAMPAIGNS_DIR):
        for f in os.listdir(CAMPAIGNS_DIR):
            if f.endswith(".json") and "_leads" not in f:
                cid = f.replace(".json", "")
                s = get_campaign_status(cid)
                if "error" not in s:
                    campaigns.append(s)
    return campaigns

def generate_daily_report() -> str:
    campaigns = list_campaigns()
    
    if not campaigns:
        return "Žiadne aktívne kampane."
    
    report = "📊 DENNÝ REPORT - Tvojton AI\n"
    report += "=" * 35 + "\n"
    report += f"Dátum: {datetime.now().strftime('%d.%m.%Y')}\n\n"
    
    total_contacted = 0
    total_interested = 0
    total_remaining = 0
    
    for camp in campaigns:
        if camp["status"] == "running":
            total_contacted += camp["contacted"]
            total_interested += camp["interested"]
            total_remaining += camp["remaining"]
            
            report += f"🎯 {camp['target']}\n"
            report += f"   Status: 🟢 Aktívna\n"
            report += f"   Oslovených: {camp['contacted']}/{camp['limit']}\n"
            report += f"   Zainteresovaných: {camp['interested']}\n"
            report += f"   Zostáva: {camp['remaining']}\n\n"
    
    if campaigns:
        report += "📈 SÚHRN:\n"
        report += "-" * 20 + "\n"
        report += f"Celkom oslovených: {total_contacted}\n"
        report += f"Celkom zainteresovaných: {total_interested}\n"
        report += f"Zostáva kontaktov: {total_remaining}\n"
        if total_contacted > 0:
            rate = round(total_interested / total_contacted * 100, 1)
            report += f"Response rate: {rate}%\n"
    
    return report

def send_daily_report() -> Dict:
    report = generate_daily_report()
    success = send_telegram(report)
    return {"sent": success, "report": report}

async def run_daily_campaign_step() -> Dict:
    campaigns = list_campaigns()
    results = []
    
    for camp in campaigns:
        if camp["status"] == "running" and camp["remaining"] > 0:
            result = await run_campaign_step(camp["id"])
            results.append({
                "campaign_id": camp["id"],
                "result": result
            })
            
            if camp["remaining"] - 1 <= 0:
                pass
    
    if results:
        send_daily_report()
    
    return {"processed": len(results), "results": results}

def get_next_run_time() -> str:
    now = datetime.now()
    next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
    
    if now.hour >= 9:
        next_run += timedelta(days=1)
    
    return next_run.isoformat()
