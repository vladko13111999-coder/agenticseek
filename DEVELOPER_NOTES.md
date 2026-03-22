# Tvojton AI - Developer Notes
**Dátum:** 22. marec 2026  
**Verzia:** 1.6.0

---

## Stav projektu

### Funkčné veci ✅

1. **Streaming chat** - Text sa zobrazuje postupne cez SSE
2. **Myšlienkový postup** - Zobrazuje sa pod správou agenta s detailami
3. **Výber modelu** - Dropdown v headeri (Twin Light, Twin Pro, Twin Research, Coder Agent)
4. **Rýchle akcie** - Obrázok, Konkurencia, SEO blog, Analýza URL, Nový Skill
5. **Detekcia jazyka** - Automatické rozpoznanie SK/CS/HR/EN
6. **Generovanie obrázkov** - SDXL Turbo, automaticky sa unloaduje po generovaní
7. **URL analýza** - Stiahne obsah webu a analyzuje ho
8. **Skill generator** - Vytváranie Python skillov cez Coder Agent
9. **Zoznam skillov** - Endpoint `/skills` vracia dostupné skilly
10. **Používateľove správy** - Zobrazujú sa v chate vpravo

### Čo treba opraviť ❌

1. **VRAM 90%+** - RTX A5000 je pomalý pre veľké modely
   - qwen2.5:14b potrebuje 62s na načítanie = 75s celkom
   - gemma3:4b je rýchlejší (~10s)
   
2. **Rýchlosť modelov:**
   - qwen2.5:14b - 75s (príliš pomalý)
   - qwen2.5-coder:14b - ešte pomalší (pre skilly)
   - gemma3:12b - ~10s (použiteľné)
   - gemma3:4b - ~10s (najrýchlejší)

3. **Video generovanie** - Disabled (potrebuje viac VRAM)

---

## API Endpoints

### `/stream-query` (POST)
Hlavný streaming endpoint pre chat.

```json
{
  "query": "Ahoj",
  "history": [...],
  "model": "gemma3:12b"
}
```

**Responsy SSE:**
- `type: "thoughts"` - Myšlienkový postup
- `type: "chunk"` - Časť textu
- `type: "image"` - Vygenerovaný obrázok (base64)
- `type: "done"` - Koniec odpovede

### `/generate-skill` (POST)
Vytvorí nový skill cez Coder Agent.

```json
{
  "description": "Funkcia na posielanie emailov"
}
```

**Responsy:**
```json
{
  "success": true,
  "name": "Posielanie Emailov",
  "path": "/workspace/agenticseek/skills/Posielanie_Emailov.md",
  "content": "# Posielanie Emailov\n..."
}
```

### `/skills` (GET)
Zoznam dostupných skillov.

### `/skills/{name}` (GET)
Detail konkrétneho skillu.

### `/health` (GET)
Health check endpoint.

---

## Modely (Brand Names)

| Model ID | Brand Name | Použitie |
|----------|------------|----------|
| gemma3:4b | Twin Light | Rýchle odpovede |
| gemma3:12b | Twin Pro | Hlavný chat |
| qwen2.5:14b | Twin Research | Analýza |
| qwen2.5-coder:14b | Coder Agent | Skill generator |
| sdxl-turbo | Image Studio | Obrázky |

---

## Konfigurácia RunPod

- **IP:** 194.26.196.212
- **Port:** 31006 (SSH), 7777 (API)
- **API URL:** https://37gt7a0hmcbdqm-7777.proxy.runpod.net
- **VRAM:** RTX A5000 (24GB)

### Restart API
```bash
ssh -i ~/.ssh/id_ed25519 -p 31006 root@194.26.196.212
cd /workspace/agenticseek
pkill -f simple_api
nohup python3 -u simple_api.py > /tmp/api.log 2>&1 &
```

---

## Repositáre

- **Frontend:** https://github.com/vladko13111999-coder/Tvojton- (branch: developer)
- **Backend:** https://github.com/vladko13111999-coder/agenticseek (branch: developer)

---

## Čo robiť ďalej

1. **Zvážiť upgrade GPU** - RTX 4090 alebo A100 pre rýchlejšie modely
2. **Optimalizovať VRAM** - Loading/unloading modelov
3. **Video generovanie** - Keď bude viac VRAM
4. **Skill systém** - Použitie vygenerovaných skillov v chate
5. **Databáza skillov** - SQLite namiesto súborov

---

## Dnešné zmeny (22.3.2026)

1. ✅ Pridaný skill generator s qwen2.5-coder:14b
2. ✅ Skilly sa ukladajú do `/workspace/agenticseek/skills/`
3. ✅ Auto-detekcia "vytvor skill" v texte
4. ✅ Nový button "Nový Skill" v UI
5. ✅ Endpoint `/skills` pre zoznam skillov
6. ✅ Otestované - skill sa úspešne vygeneroval a uložil
