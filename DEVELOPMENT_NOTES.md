# Development Notes - agenticseek

## 📌 Projekt Status - Sun Mar 22 2026

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

# 3. INŠTALÁCIA PYTHON závislostí pre AI generovanie
pip3 install torch==2.5.1 diffusers==0.30.0 transformers==4.46.0 accelerate==0.26.0 imageio imageio-ffmpeg pillow numpy

# 4. SPUSTENIE OLLAMA DAEMON
export OLLAMA_HOST=0.0.0.0:11434
ollama serve &

# 5. SPUSTENIE API
cd ~/agenticseek
python3 simple_api.py
# API beží na http://0.0.0.0:7777
```

### RunPod Konfigurácia (RTX A5000 - 24GB VRAM)

| Nastavenie | Hodnota |
|------------|---------|
| Exposed HTTP Ports | 7777 |
| GPU | NVIDIA RTX A5000 (24GB VRAM) |
| VRAM použitie | ~11GB (chat + obrázky + videá) |

### CORS Nastavenia

API povoluje prístup z:
- https://tvojton.online
- https://www.tvojton.online
- http://localhost:3000
- http://localhost:5173
- * (všetky - pre vývoj)

---

## 🆕 BRAND TWIN UPDATE (2026-03-22)

### Brand Twin - Autonómny obchodný asistent
- **Účel:** E-shopy a malé firmy - komunikácia, SEO, reklamácie, generovanie obsahu
- **Jazyky:** SK, CZ, HR, EN (automatická detekcia)
- **Model:** gemma3:12b
- **Identita:** Reprezentuje tvojton.online

### 🎨 GENEROVANIE OBSAHU (NOVÉ!)

#### Obrázky
- **Model:** SDXL Turbo (stabilityai/sdxl-turbo)
- **VRAM:** ~7GB
- **Rozlíšenie:** 512x512 (default)
- **Kvalita:** 4 inference steps (rýchle)

#### Videá
- **Model:** Zeroscope v2 (cerspense/zeroscope_v2_576w)
- **VRAM:** ~3.7GB
- **Formát:** GIF (16 snímkov, fps=8)
- **Rozlíšenie:** 256x256

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
Agent: "Iný? Nepíšem stále dokola 'Ako vám dnes môžem pomôcť?'. To by ma nudilo."
```

---

## 📁 ŠTRUKTÚRA PROJEKTU

```
agenticseek/
├── simple_api.py              # Hlavný API server (odporúčaný) - port 7777
│                              # Obsahuje: chat, image, video generovanie
├── api.py                     # Pôvodný komplexný API server
├── config.ini                 # Konfigurácia modelov a jazykov
├── requirements.txt           # Python dependencies
├── .env                      # Environment variables
├── sources/
│   ├── agent_router.py       # Request routing & language detection
│   ├── browser.py            # Chrome/Selenium setup
│   ├── llm_provider.py      # LLM provider (Ollama)
│   └── agents/
│       └── casual_agent.py   # Brand Twin chat agent
└── prompts/base/
    └── casual_agent.txt      # Brand Twin prompt
```

---

## 🔧 KONFIGURÁCIA

### simple_api.py (odporúčaný)

Jednoduchý API server s vestavěným:
- Chat (Ollama gemma3:12b)
- Obrázky (SDXL Turbo)
- Videá (Zeroscope)
- Automatická detekcia jazyka
- Automatická detekcia požiadavky (text/image/video)

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

### API Endpoints (simple_api.py)

| Endpoint | Metóda | Popis |
|---------|--------|-------|
| `/health` | GET | Zdravie API, VRAM, stav modelov |
| `/query` | POST | Chat + automatické generovanie obrázkov/videí |
| `/generate-image` | POST | Priame generovanie obrázkov |
| `/generate-video` | POST | Priame generovanie videí (GIF) |

### Automatické smerovanie

`/query` endpoint automaticky detekuje:
- **Text požiadavka:** Chat odpoveď
- **Obrázok požiadavka:** "vygeneruj obrazok..." → generuje obrázok
- **Video požiadavka:** "vygeneruj video..." → generuje video (GIF)

### Jazyková detekcia
- Automatická detekcia: SK, CS, HR, EN
- Odpoveď v jazyku používateľa
- Priorita: Slovak > Czech > Croatian > English

---

## 🚀 SPUSTENIE API

### Odporúčaný spôsob (simple_api.py)

```bash
cd ~/agenticseek
export OLLAMA_HOST=0.0.0.0:11434
python3 simple_api.py

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

# Generovanie obrázka
curl -X POST http://localhost:7777/query \
  -H "Content-Type: application/json" \
  -d '{"query": "vygeneruj obrazok slnecnice"}'

# Generovanie videa
curl -X POST http://localhost:7777/query \
  -H "Content-Type: application/json" \
  -d '{"query": "vygeneruj videoacky a pes beha"}'

# Priame generovanie obrázka
curl -X POST http://localhost:7777/generate-image \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a beautiful sunset"}'

# Priame generovanie videa
curl -X POST http://localhost:7777/generate-video \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a cat walking"}'
```

---

## ⚠️ ZNÁME PROBLÉMY

### 1. Jazyková detekcia (OPRAVENÉ)
- gemma3:12b má tendenciu odpovedať po česky
- **Riešenie:** Explicitné "SLOVAK ONLY" v system prompt

### 2. VRAM obmedzenia
- Pri generovaní videí musí byť SDXL unloadnutý
- Alebo použiť menšie rozlíšenie
- Celkom: ~11GB VRAM (chat + obrázky + videá)

### 3. Translation modely (neblokujúce)
```
Failed to load en-sk: Due to a serious vulnerability issue in torch.load...
```
- Modele Helsinki-NLP a M2M100 sa nenačítajú
- Príčina: torch verzia < 2.6 má CVE zraniteľnosť

### 4. Speech-to-Text (neblokujúce)
```
Could not import the PyAudio C module '_portaudio'.
Speech To Text disabled.
```
- STT je disabled, API funguje bez neho

---

## 📋 CHECKLIST PO RESETE

- [x] nainštalovať Ollama
- [x] stiahnuť gemma3:12b
- [ ] nainštalovať Python dependencies (torch, diffusers, etc.)
- [x] spustiť ollama serve
- [x] spustiť python simple_api.py
- [ ] overiť /health endpoint
- [ ] otestovať chat v SK/CZ/HR/EN
- [ ] otestovať generovanie obrázkov
- [ ] otestovať generovanie videí

---

## 📝 COMMITY

| Commit | Popis |
|--------|-------|
| `aae3275` | feat: Add image/video generation with SDXL and Zeroscope |
| `5057cfa` | feat: Add CORS middleware for tvojton.online |
| `8a00015` | feat: Brand Twin multilingual support (SK, CZ, HR, EN) |
| `4d910de` | feat: update API, frontend routing, casual agent |
| `ec6962a` | fix: add Chrome options for container/headless |
| `597125d` | fix: improve chat language detection |

---

## 🎯 BUDÚCE VYLEPŠENIA

1. **Vyššie rozlíšenie obrázkov** - SDXL s 1024x1024
2. **Kvalitnejšie videá** - LTX-Video alebo SVD
3. **Streaming odpovedí** - Pre dlhšie odpovede
4. **Cache generovaných obrázkov** - Pre opakované požiadavky
5. **User profily** - Personalizácia konverzácií

---

**Posledná aktualizácia:** 2026-03-22 09:45 UTC  
**Branch:** main
