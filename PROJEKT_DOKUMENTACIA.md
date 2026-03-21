# Brand Twin AI - Kompletná Dokumentácia

**Posledná aktualizácia:** 21.03.2026
**Verzia:** 2.0

---

## Rýchly Prehľad

**Projekt:** Brand Twin AI asistent pre tvojton.online
**Účel:** AI chat bot pre e-shopy a malé firmy (komunikácia, SEO, reklamácie)
**Jazyky:** Slovenčina, Čeština, Chorvatčina, Angličtina

### Architektúra
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   API Backend   │────▶│     Ollama      │
│  (tvojton.online)     │  (Lightning.ai) │     │  (gemma3:12b)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
      Vercel                  Port 7777           Lightning Studio
```

---

## 1. Repozitáre

### 1.1 agenticseek (Backend API)
- **GitHub:** https://github.com/vladko13111999-coder/agenticseek
- **Platforma:** Lightning.ai Studios
- **Studio URL:** https://lightning.ai/vladko13111999/intelligent-agent-platform-project/studios/consistent-fuchsia-cseqj
- **Cloudspace ID:** 01km8p7wqj629zs2hpb8sc2bya

### 1.2 Tvojton- (Frontend)
- **GitHub:** https://github.com/vladko13111999-coder/Tvojton-
- **Platforma:** Vercel
- **URL:** https://tvojton.online/agent
- **Vercel Project ID:** prj_Txp8DZDU9FyR6iv9yR6wSUJciCYR

### 1.3 OpenClaw (Orchestrátor)
- **GitHub:** https://github.com/openclaw/openclaw
- **Verzia:** 2026.3.14
- **Lokalita:** /teamspace/studios/this_studio/openclaw
- **Port:** 18789 (gateway, local mode)
- **Node.js:** vyžaduje >=22.16.0 (aktuálne používané: 22.22.1)

---

## 2. Dôležité URL

| Služba | URL |
|--------|-----|
| **Frontend (Vercel)** | https://tvojton.online/agent |
| **API Backend** | https://7777-01km8p7wqj629zs2hpb8sc2bya.cloudspaces.litng.ai |
| **API Health** | https://7777-01km8p7wqj629zs2hpb8sc2bya.cloudspaces.litng.ai/health |
| **API Query** | https://7777-01km8p7wqj629zs2hpb8sc2bya.cloudspaces.litng.ai/query |
| **OpenClaw Gateway** | ws://localhost:18789 |
| **OpenClaw Health** | http://localhost:18789/health |

---

## 3. Spustenie Backend (Lightning.ai Studio)

### 3.1 Automatické spustenie (odporúčané)

Studio má nastavený `on_start.sh` ktorý automaticky spustí:
1. Ollama server (port 11434)
2. Brand Twin API (port 7777)

### 3.2 Manuálne spustenie

```bash
# 1. Spustiť Ollama
export OLLAMA_HOST=0.0.0.0:11434
ollama serve &

# 2. Spustiť API
cd /teamspace/studios/this_studio/agenticseek
python simple_api.py
```

### 3.3 Port Forwarding na Lightning.ai

Pre prístup k API z externe:
1. Otvor studio v prehliadači: https://lightning.ai/.../studios/...
2. Klikni na **Ports** alebo **Forward Port** v UI
3. Alebo použi priamu URL: `https://<PORT>-<CLOUDSPACE_ID>.cloudspaces.litng.ai`

**Verejná URL pre port 7777:**
```
https://7777-01km8p7wqj629zs2hpb8sc2bya.cloudspaces.litng.ai
```

---

## 4. OpenClaw Orchestrátor

### 4.1 Konfigurácia

OpenClaw je nakonfigurovaný pre orchestráciu Brand Twin AI:
- **Gateway port:** 18789
- **Mode:** local (loopback bind)
- **Default model:** ollama/gemma3:12b
- **Auth profile:** ollama:default (nakonfigurovaný v auth-profiles.json)

### 4.2 Spustenie OpenClaw

```bash
# Nastavenie Node.js 22.22.1 (vyžadované >=22.16.0)
unset npm_config_prefix
export PATH="/teamspace/studios/this_studio/.nvm/versions/node/v22.22.1/bin:$PATH"

# Spustenie gateway
cd /teamspace/studios/this_studio/openclaw
node dist/index.js gateway run --bind loopback --port 18789
```

### 4.3 Overenie statusu

```bash
# Health check
curl http://localhost:18789/health

# Model status
cd /teamspace/studios/this_studio/openclaw
node dist/index.js models status
```

### 4.4 Auth Profile pre Ollama

Auth profile je uložený v: `~/.openclaw/agents/main/agent/auth-profiles.json`

Obsahuje:
```json
{
  "version": 1,
  "profiles": {
    "ollama:default": {
      "type": "api_key",
      "provider": "ollama",
      "key": "ollama-local-placeholder-key-2026"
    }
  }
}
```

---

## 5. Inštalované Modely (Ollama)

| Model | Veľkosť | Použitie |
|-------|---------|----------|
| gemma3:12b | 8.1 GB | Hlavný chat model |

**Príkazy pre správu modelov:**
```bash
ollama list                    # Zobraziť modely
ollama pull <model>           # Stiahnuť model
ollama rm <model>            # Vymazať model
```

---

## 6. API Endpoints

### 6.1 /health
```bash
curl https://7777-01km8p7wqj629zs2hpb8sc2bya.cloudspaces.litng.ai/health
```
**Odpoveď:**
```json
{"status":"healthy","version":"1.0.0","provider":"ollama"}
```

### 6.2 /query
```bash
curl -X POST https://7777-01km8p7wqj629zs2hpb8sc2bya.cloudspaces.litng.ai/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Ahoj, ako sa máš?"}'
```
**Odpoveď:**
```json
{
  "done": "true",
  "answer": "Ahoj! Mám sa dobre, ďakujem za opýtanie!",
  "reasoning": "",
  "agent_name": "TvojTon",
  "success": "true",
  "blocks": {},
  "status": "Ready",
  "uid": "test-123"
}
```

---

## 7. Kľúčové Súbory

### Backend (/agenticseek)

| Súbor | Popis |
|-------|-------|
| `simple_api.py` | Zjednodušený FastAPI server (aktívny) |
| `api.py` | Pôvodný komplexný API server |
| `config.ini` | Konfigurácia (model, porty, agenty) |
| `.env` | API kľúče a tokeny |
| `on_start.sh` | Automatické spustenie pri štarte |

### Frontend (/Tvojton-/client)

| Súbor | Popis |
|-------|-------|
| `src/lib/agentApi.ts` | API klient - TU NASTAV VITE_API_URL |
| `src/components/BrandTwinChat.tsx` | Hlavný chat komponent |

---

## 8. Konfigurácia Vercel

### Environment Variables (nastavené)
```
VITE_API_URL = https://7777-01km8p7wqj629zs2hpb8sc2bya.cloudspaces.litng.ai
```

### Zmena Vercel Environment Variable
```bash
VERCEL_TOKEN="vcp_..."
PROJECT_ID="prj_Txp8DZDU9FyR6iv9yR6wSUJciCYR"
ENV_ID="RCedGALm2koQIyIP"

curl -X PATCH "https://api.vercel.com/v6/projects/${PROJECT_ID}/env/${ENV_ID}" \
  -H "Authorization: Bearer $VERCEL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": "https://NOVA-URL", "target": ["production", "preview", "development"]}'
```

### Trigger Redeploy
```bash
cd Tvojton-
git commit --allow-empty -m "Redeploy" && git push origin main
```

---

## 9. Predchádzajúca Infraštruktúra (historické)

### RunPod (už nepoužívané)
- **Server:** RunPod (pozri starú dokumentáciu)
- **API URL:** https://ii5nrun0ci2ahz-7777.proxy.runpod.net

---

## 10. Troubleshooting

### API nedostupné
```bash
# 1. Skontrolovať či beží
ps aux | grep python | grep simple_api

# 2. Reštartovať API
pkill -f simple_api
cd /teamspace/studios/this_studio/agenticseek
nohup python simple_api.py > simple_api.log 2>&1 &

# 3. Skontrolovať logy
cat /teamspace/studios/this_studio/agenticseek/simple_api.log
```

### Ollama nefunguje
```bash
# 1. Skontrolovať či beží
ps aux | grep ollama | grep -v grep

# 2. Reštartovať
pkill -f ollama
export OLLAMA_HOST=0.0.0.0:11434
ollama serve &

# 3. Test
curl http://localhost:11434/api/tags
```

### Frontend sa nepripája k API
1. Skontrolovať CORS v `simple_api.py`
2. Skontrolovať `VITE_API_URL` vo Vercel environment variables
3. Trigger redeploy

---

## 11. Credentials a Tokens

### Svetlé (uložené v dokumentácii)
- **GitHub:** vladko13111999-coder
- **Vercel Team ID:** team_t6c658eNPFC3jN1uyx5dbsLQ
- **Vercel Project ID:** prj_Txp8DZDU9FyR6iv9yR6wSUJciCYR

### Tajné (v .env súboroch)
- **Vercel Token:** `vcp_...` (pozri Vercel dashboard)
- **GitHub Token:** `ghp_...` (pozri GitHub settings)
- **Lightning.ai Token:** UUID formát (pozri Lightning settings)

---

## 12. Štruktúra Kódu

```
/teamspace/studios/this_studio/
├── agenticseek/              # Backend repo
│   ├── simple_api.py         # Jednoduchý FastAPI server
│   ├── api.py                # Pôvodný komplexný server
│   ├── config.ini            # Konfigurácia
│   ├── .env                  # Environment variables
│   ├── sources/              # Zdrojové súbory
│   │   ├── agents/          # AI agenty
│   │   ├── llm_provider.py  # LLM provider
│   │   └── agent_router.py  # Routing
│   └── on_start.sh          # Auto-spustenie
│
├── Tvojton-/                 # Frontend repo
│   ├── client/              # Next.js/Vite frontend
│   │   ├── src/lib/agentApi.ts  # API klient
│   │   └── .env.production  # Production env
│   ├── server/              # Backend server (ak treba)
│   └── vercel.json          # Vercel konfigurácia
│
└── .lightning_studio/       # Lightning.ai konfigurácia
    ├── on_start.sh          # Auto-spustenie služieb
    └── .studiorc             # Studio settings
```

---

## 13. Rýchly Štart (Pristupenie k projektu)

```bash
# 1. Klonovať repozitáre
git clone https://github.com/vladko13111999-coder/agenticseek.git
git clone https://github.com/vladko13111999-coder/Tvojton-.git

# 2. Otvoriť Lightning.ai Studio
# https://lightning.ai/vladko13111999/intelligent-agent-platform-project/studios/consistent-fuchsia-cseqj

# 3. API je už spustené na:
# https://7777-01km8p7wqj629zs2hpb8sc2bya.cloudspaces.litng.ai

# 4. Frontend je na:
# https://tvojton.online/agent

# 5. Pre zmeny v backend:
cd agenticseek
nano simple_api.py
# Po úprave reštartovať:
pkill -f simple_api && python simple_api.py &

# 6. Pre zmeny vo frontende:
cd Tvojton-
# Uprav súbory a pushni - Vercel automaticky deployne
git add . && git commit -m "zmena" && git push
```

---

## 14. Budúce Vylepšenia

1. **Generovanie obrázkov** - Stable Diffusion integrácia
2. **Generovanie videí** - Stable Video Diffusion
3. **Text-to-Video** - Priamo z textu
4. **Užívateľské profily** - Personalizácia konverzácií
5. **Webhooky** - Notifikácie pre status generovania

---

*Dokumentácia aktualizovaná: 21.03.2026*
*Verzia: 2.0*
