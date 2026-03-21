# Brand Twin AI - Kompletná Dokumentácia

## Prehľad Projektov

Máme 2 hlavné repozitáre:
1. **agenticseek** - Backend API (RunPod server)
2. **Tvojton-** - Frontend (Vercel deployment)

---

## 1. Repozitáre

### agenticseek (Backend)
- **GitHub**: https://github.com/vladko13111999-coder/agenticseek
- **Server**: RunPod (pozri .env pre SSH credentials)
- **API URL**: pozri .env
- **Port**: 7777

### Tvojton- (Frontend)
- **GitHub**: https://github.com/vladko13111999-coder/Tvojton-
- **URL**: https://tvojton.online/agent

---

## 2. Spustenie Backend

```bash
# SSH na RunPod
ssh -i /tmp/runpod_key -p 52213 root@IP_ADRESA  # pozri .env

# Ísť do adresára
cd /agenticseek

# Aktivovať virtual env
source venv/bin/activate

# Spustiť API
OLLAMA_HOST=http://localhost:11434 python api.py
```

### Spustenie Telegram Bota (samostatne)
```bash
cd /agenticseek
source venv/bin/activate
python telegram_bot.py
```

---

## 3. Inštalované Modely

| Model | Veľkosť | Použitie |
|-------|---------|----------|
| qwen2.5:14b | 9.0 GB | Hlavný LLM |
| gemma3:12b | 8.1 GB | Chat |
| x/flux2-klein | 5.7 GB | Multimodal (obrázky) |
| Stable Diffusion 1.5 | - | Generovanie obrázkov |
| Stable Video Diffusion XT | - | Generovanie videí |

---

## 4. Kľúčové Súbory

### Backend (/agenticseek)

| Súbor | Popis |
|-------|-------|
| `api.py` | Hlavný FastAPI server |
| `brand_twin_api.py` | Stable Diffusion pre obrázky |
| `video_generator.py` | Stable Video Diffusion pre videá |
| `web_browser.py` | Playwright pre web browsing |
| `telegram_bot.py` | Telegram bot |
| `sources/agent_router.py` | Routing požiadaviek |
| `.env` | API kľúče a tokeny |

### Frontend (/Tvojton-/client)

| Súbor | Popis |
|-------|-------|
| `src/pages/Agent.tsx` | Hlavná stránka agenta |
| `src/components/AIChatBox.tsx` | Komponent chatu |
| `src/lib/agentApi.ts` | API klient |

---

## 5. API Endpoints

| Endpoint | Metóda | Popis |
|----------|--------|-------|
| `/query` | POST | Hlavný endpoint pre AI |
| `/health` | GET | Zdravotná kontrola |
| `/generate` | POST | Marketing generovanie |
| `/generate_video` | POST | Video generovanie |

### Príklad /query
```bash
curl -X POST "API_URL/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Ahoj, ako sa máš?"}'
```

### Odpoveď
```json
{
  "done": "true",
  "answer": "Ahoj! Mam sa dobre, dakujem.",
  "image_base64": "...",
  "video_base64": "...",
  "agent_name": "casual"
}
```

---

## 6. Funkcie Agenta

### 6.1 Chat s pamäťou
- Konverzačná pamäť medzi správami
- Pamäť sa ukladá do súboru
- Jazyková detekcia (SK/CZ/EN)

### 6.2 Generovanie obrázkov
- **Model**: Stable Diffusion 1.5
- **Endpoint**: Automaticky detekované kľúčovými slovami
- **Keywords**: "vygeneruj obrázok", "sprav obrázok", "generuj"
- Výstup: base64 encoded PNG

### 6.3 Generovanie videí
- **Model**: Stable Video Diffusion XT
- **Typ**: Image-to-video (najprv obrázok, potom video)
- **Keywords**: "vygeneruj video", "sprav video", "vytvor klip"
- Výstup: base64 encoded MP4

### 6.4 Web browsing
- **Technológia**: Playwright + Chromium
- **Súbor**: `web_browser.py`
- Používa sa pre analýzu URL

---

## 7. Telegram Bot

### Konfigurácia
- Token nájdeš v `.env` subore
- Bot username pozri u @BotFather

### Príkazy
- `/start` - Úvodná správa
- `/help` - Pomoc
- `/newchat` - Nový rozhovor

### Spustenie
```bash
cd /agenticseek
source venv/bin/activate
python telegram_bot.py
```

---

## 8. Deploy na Vercel

```bash
cd /tmp/Tvojton-
npx vercel --prod --token VERCEL_TOKEN  # pozri .env subor
```

---

## 9. Agent Router

Súbor: `sources/agent_router.py`

### Kľúčové slová pre routing:

**Image keywords:**
- vygeneruj.*obrázok, sprav.*obrázok, generate.*image, create.*picture, nakresli, namaluj

**Video keywords:**
- sprav.*video, vygeneruj.*video, vytvor.*klip, make.*video, animuj

**Planner keywords:**
- nájdi.*a, vyhľadaj.*a.*zhrň, find.*and, research, analyze

---

## 10. Známe Problémy a Riešenia

### Problém: API nedostupné
```bash
# Reštart API
pkill -9 python
cd /agenticseek
source venv/bin/activate
OLLAMA_HOST=http://localhost:11434 python api.py
```

### Problém: Telegram bot nefunguje
```bash
# Skontrolovať .env
cat /agenticseek/.env | grep TELEGRAM

# Reštart
pkill -f telegram_bot
python telegram_bot.py
```

### Problém: Chýba modul
```bash
source venv/bin/activate
pip install <modul>
```

---

## 11. Credentials (v .env subore)

Všetky sensitive údaje sú v `/agenticseek/.env`:
- RunPod IP a port
- Vercel token
- Telegram bot token
- GitHub token

---

## 12. Budúce Vylepšenia

1. **Text-to-Video** - Priamo z textu bez obrázka
2. **FLUX.2 Klein** - Plná integrácia pre lepšiu kvalitu
3. **A/B testovanie** - Rôzne prompty
4. **Užívateľské profily** - Personalizácia
5. **Webhooky** - Notifikácie pre status generovania

---

## 13. Štruktúra Kódu

```
/agenticseek/
├── api.py                 # Main FastAPI app
├── brand_twin_api.py      # Image generation (Stable Diffusion)
├── video_generator.py     # Video generation (SVD)
├── web_browser.py         # Web browsing (Playwright)
├── telegram_bot.py        # Telegram bot
├── .env                   # Environment variables
├── sources/
│   ├── agent_router.py   # Request routing
│   ├── agents/           # AI agents
│   │   ├── casual_agent.py
│   │   ├── planner_agent.py
│   │   └── ...
│   └── memory.py         # Conversation memory
└── venv/                 # Virtual environment

/Tvojton-/client/
├── src/
│   ├── pages/
│   │   └── Agent.tsx     # Main agent page
│   ├── components/
│   │   └── AIChatBox.tsx # Chat component
│   └── lib/
│       └── agentApi.ts   # API client
└── package.json
```

---

## 14. Tipy pre Pokračovanie

1. **Pri zmene API** - Uprav `api.py` a reštartuj server
2. **Pri zmene Frontendu** - Push na GitHub, Vercel automaticky deployne
3. **Pri zmene Modelov** - Stiahni cez `ollama pull <model>`
4. **Pri zmene Route** - Uprav `agent_router.py`
5. **Logy** - `tail -50 /agenticseek/api.log`

---

## 15. Rýchly Štart (Ak začíname znova)

```bash
# 1. Klonovať repo
git clone https://github.com/vladko13111999-coder/agenticseek.git
git clone https://github.com/vladko13111999-coder/Tvojton-.git

# 2. SSH na RunPod a stiahnuť zmeny
cd /agenticseek && git pull origin main

# 3. Spustiť API
cd /agenticseek && source venv/bin/activate
OLLAMA_HOST=http://localhost:11434 python api.py

# 4. V novom terminali spustiť Telegram bota
cd /agenticseek && source venv/bin/activate
python telegram_bot.py

# 5. Frontend je na Vercel - automaticky aktualizovaný
```

---

## 16. Dôležité URL

- **Frontend**: https://tvojton.online/agent
- **API Health**: https://ii5nrun0ci2ahz-7777.proxy.runpod.net/health
- **Telegram Bot**: pozri @BotFather pre username

---

*Dokumentácia vytvorená: 21.03.2026*
*Verzia: 1.0*
