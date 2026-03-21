# Development Notes - agenticseek

## 📌 Projekt Status - Sat Mar 21 2026

---

## 🚀 PRODUKČNÉ NASTAVENIE (RUNPOD)

### DÔLEŽITÉ - Po resete RunPod!

Po resete containeru na RunPod je potrebné znova nainštalovať všetko:

```bash
# 1. INŠTALÁCIA OLLAMA
curl -fsSL https://ollama.com/install.sh | sh

# 2. STAHOVANIE MODELOV (celkom ~15GB)
ollama pull gemma3:12b    # Pre casual chat (Brand Twin) - ~7GB
ollama pull qwen2.5:14b   # Pre vyhľadávanie, obrázky, videá - ~8GB

# 3. OVERENIE
ollama list
# Malo by ukázať:
# gemma3:12b
# qwen2.5:14b

# 4. SPUSTENIE OLLAMA DAEMON
ollama serve &
# Alebo nastaviť ako service

# 5. INŠTALÁCIA CHROMIUM (pre web browsing agenta)
apt-get update && apt-get install -y chromium-browser chromium-chromedriver

# 6. INŠTALÁCIA PYTHON závislostí
pip3 install -r requirements.txt

# 7. SPUSTENIE API
cd ~/agenticseek
python3 api.py
# API beží na http://0.0.0.0:7777
```

### RunPod Konfigurácia

| Nastavenie | Hodnota |
|------------|---------|
| Exposed HTTP Ports | 7777, 3000 |
| Environment Variables | WORK_DIR=/tmp/agenticseek |
| GPU | NVIDIA L40 (45GB VRAM) |

### CORS Nastavenia

API povoluje prístup z:
- https://tvojton.online
- https://www.tvojton.online
- http://localhost:3000
- http://localhost:5173

---

## 🆕 BRAND TWIN UPDATE (2026-03-21)

### Brand Twin - Autonómny obchodný asistent
- **Účel:** E-shopy a malé firmy - komunikácia, SEO, reklamácie, generovanie obsahu
- **Jazyky:** SK, CZ, HR, EN
- **Model:** gemma3:12b (dokým nebude GaMS3)
- **Identita:** Reprezentuje tvojton.online

### Brand Twin Osobnosť
- Priateľský, suchý humor (anglický štýl)
- Pri vážnych veciach (reklamácie, problémy) - profesionálny, bez humoru
- Nikdy vulgárny alebo sarkastický na úkor používateľa
- Odpovedá v jazyku používateľa

### Suchý Humor Príklady
```
User: "Môžeš mi pomôcť s reklamáciou?"
Agent: "Samozrejme, reklamácie sú moja obľúbená zábava. Ale poďme na to."

User: "Si nejaký iný ako ostatní chatboti?"
Agent: "Iný? Povedzme, že neopakujem stále dokola 'Ako vám dnes môžem pomôcť?'. To by ma nudilo."
```

---

## 📁 ŠTRUKTÚRA PROJEKTU

```
agenticseek/
├── api.py                      # Main FastAPI server (port 7777)
├── config.ini                  # Konfigurácia modelov a jazykov
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
├── sources/
│   ├── agent_router.py         # Request routing & language detection
│   ├── browser.py              # Chrome/Selenium setup
│   ├── llm_provider.py         # LLM provider (Ollama)
│   └── agents/
│       └── casual_agent.py     # Brand Twin chat agent
├── prompts/base/
│   └── casual_agent.txt        # Brand Twin prompt
├── frontend/                   # (deprecated, používa sa Tvojton-)
└── brand_twin_api.py           # Image generation
```

---

## 🔧 KONFIGURÁCIA

### config.ini
```ini
[MAIN]
provider_name = ollama
provider_model = gemma3:12b
provider_server_address = http://localhost:11434
languages = sk,cs,hr,en

[AGENTS]
casual_model = gemma3:12b
image_model = qwen2.5:14b
video_model = qwen2.5:14b
planner_model = gemma3:12b
```

### .env
```env
WORK_DIR=/tmp/agenticseek
DOCKER_INTERNAL_URL=http://localhost
```

---

## ✅ FUNKČNÉ VECI

### Agent Router (`sources/agent_router.py`)
- Automaticky smeruje požiadavky na správneho agenta
- Podporované agenty: `casual` (chat), `image`, `video`, `planner`
- Detekcia jazyka: SK, CS, HR, EN
- Rozšírená detekcia s porovnávaním podobných jazykov (SK vs CS)

### API Endpoints
| Endpoint | Metóda | Popis |
|----------|--------|-------|
| `/health` | GET | Zdravie API |
| `/query` | POST | Poslať správu chatbotovi |
| `/models` | GET | Zoznam dostupných modelov |

### CORS
Povolené origins:
- tvojton.online
- www.tvojton.online
- localhost:3000, localhost:5173

---

## ⚠️ ZNÁME PROBLÉMY

### 1. Translation modely (neblokujúce)
```
Failed to load en-sk: Due to a serious vulnerability issue in torch.load...
```
- Modely Helsinki-NLP a M2M100 sa nenačítajú
- Príčina: torch verzia < 2.6 má CVE zraniteľnosť
- **Riešenie:** Upgrade torch na >= 2.6 (voliteľné)

### 2. Speech-to-Text (neblokujúce)
```
Could not import the PyAudio C module '_portaudio'.
Speech To Text disabled.
```
- STT je disabled, API funguje bez neho

### 3. Chrome/Chromedriver
- Potrebné nainštalovať chromium-browser a chromium-chromedriver
- Ak nie je nainštalovaný, browser agent sa preskočí (graceful fallback)

---

## 🚀 SPUSTENIE API

```bash
# Základné spustenie
cd ~/agenticseek
python3 api.py

# S GPU akceleráciou (automaticky detekované)
python3 api.py

# API beží na http://0.0.0.0:7777
```

### Testovanie
```bash
# Health check
curl http://localhost:7777/health

# Test chat
curl -X POST http://localhost:7777/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Ahoj, ako sa máš?"}'
```

---

## 📋 CHECKLIST PO RESETE

- [ ] nainštalovať Ollama
- [ ] stiahnuť gemma3:12b
- [ ] stiahnuť qwen2.5:14b
- [ ] nainštalovať chromium-browser
- [ ] nainštalovať chromium-chromedriver
- [ ] spustiť ollama serve
- [ ] spustiť python api.py
- [ ] overiť /health endpoint
- [ ] otestovať chat v SK/CZ/HR/EN

---

## 📝 COMMITY

| Commit | Popis |
|--------|-------|
| `5057cfa` | feat: Add CORS middleware for tvojton.online |
| `8a00015` | feat: Brand Twin multilingual support (SK, CZ, HR, EN) |
| `4d910de` | feat: update API, frontend routing, casual agent |
| `ec6962a` | fix: add Chrome options for container/headless |
| `597125d` | fix: improve chat language detection |

---

**Posledná aktualizácia:** 2026-03-21 16:00 UTC  
**Branch:** main
