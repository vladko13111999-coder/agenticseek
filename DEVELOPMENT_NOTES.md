# Development Notes

## 📌 Projekt Status - Sat Mar 21 2026

---

## 🆕 BRAND TWIN UPDATE (2026-03-21)

### Brand Twin - Autonómny obchodný asistent
- **Účel:** E-shopy a malé firmy - komunikácia, SEO, reklamácie, generovanie obsahu
- **Jazyky:** SK, CZ, HR, EN
- **Model:** gemma3:12b (dokým nebude GaMS3)
- **Identita:** Reprezentuje tvojton.online

### Čo bolo zmenené:

#### 1. `prompts/base/casual_agent.txt` - Brand Twin osobnosť
- Pridaná oficiálna Brand Twin identita
- Pridaný suchý humor (anglický štýl)
- Pridané CZ príklady a pravidlá
- Pridané príklady humoru pre vážne situácie

#### 2. `sources/agent_router.py` - Vylepšená detekcia jazykov
- Rozšírená detekcia SK (slovenčina) - 14 slov
- Rozšírená detekcia CS (čeština) - 16 slov
- Rozšírená detekcia HR (chorvátčina) - 13 slov
- Rozšírená detekcia EN (angličtina) - 14 slov
- Zlepšený algoritmus rozpoznávania podobných jazykov (SK vs CS)

#### 3. `config.ini`
- Pridaný `cz` do zoznamu jazykov

---

## ✅ FUNKČNÉ VECI (Working Features)

---

## ✅ FUNKČNÉ VECI (Working Features)

### Agent Router (`sources/agent_router.py`)
- Automaticky smeruje požiadavky na správneho agenta
- Podporované agenty: `casual` (chat), `image`, `video`, `planner`
- Detekcia jazyka: slovenčina (sk), angličtina (en), chorvátčina (hr), čeština (cs)
- Funguje správne

### Chat Funkcionalita (`api.py`)
- `/query` endpoint funguje
- Language detection funguje (používa `force_lang` parameter)
- Pamäť sa čistí medzi správami (prevencia duplikácie histórie)
- Odpovede sa deduplikujú (max 3 riadky, 300 znakov)
- Tagy `<|user|>/<|assistant|>` sa odstraňujú z odpovedí

### Chrome/Selenium (`sources/browser.py`)
- Opravené Chrome options pre headless/container prostredie
- Pridané: `--disable-software-rasterizer`, `--disable-extensions`, atď.
- API štartuje bez Chrome chýb

### Frontend (`frontend/agentic-seek-front/`)
- React app s Marketing a Video tabmi
- `/static` servuje skompilované súbory
- Chat interface funguje

### Brand Twin API (`brand_twin_api.py`)
- Integrácia s GLM/Ollama na generovanie obrázkov
- Vytvorený nový súbor

---

## ⚠️ PROBLÉMY KTORÉ TREBA OPRAVIŤ

### 1. LLM Model gams3:12b - Jazykové miešanie
- **Problém:** Model občas mieša jazyky v odpovediach (hlavne čeština)
- **Príčina:** Model nedostatočne rešpektuje prompt inštrukcie
- **Riešenie:** Možno treba lepší model alebo iný prístup k lang detection

### 2. Translation modely - torch.load chyba
```
Failed to load en-sk: Due to a serious vulnerability issue in torch.load...
```
- **Problém:** Helsinki-NLP a M2M100 modely sa nenačítajú
- **Príčina:** torch verzia < 2.6 má CVE zraniteľnosť
- **Stav:** Predexistujúci problém,不影响 základnú funkčnosť
- **Treba:** Upgrade torch na >= 2.6

### 3. Speech-to-Text (PyAudio)
```
Could not import the PyAudio C module '_portaudio'.
Speech To Text disabled.
```
- **Problém:** PyAudio nie je nainštalované
- **Stav:** STT je disabled, API funguje bez neho

---

## 🔧 KONFIGURÁCIA

```
Provider: ollama
Model: gams3:12b  
Server: 127.0.0.1:11434
API Port: 7777
```

## 📁 DÔLEŽITÉ SÚBORY

| Súbor | Popis |
|-------|-------|
| `api.py` | Main FastAPI server |
| `sources/agent_router.py` | Request routing & language detection |
| `sources/browser.py` | Chrome/Selenium setup |
| `brand_twin_api.py` | Image generation |
| `prompts/base/casual_agent.txt` | Chat prompt |
| `frontend/agentic-seek-front/` | React frontend |

## 🚀 AKO ŠTARTOVAŤ

```bash
cd ~/agenticseek
python api.py
# API beží na http://0.0.0.0:7777
```

## 📝 COMMITY DNEŠNÉHO DŇA

| Commit | Popis |
|--------|-------|
| `4d910de` | feat: update API, frontend routing, casual agent and UI changes |
| `ec6962a` | fix: add Chrome options for container/headless environment |
| `597125d` | fix: improve chat language detection, memory management and response quality |

---

**Posledná aktualizácia:** 2026-03-21 14:00 UTC  
**Branch:** main
