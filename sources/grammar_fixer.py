import langid

class GrammarFixer:
    def __init__(self):
        self.langid = langid
        
    def detect_language(self, text):
        lang, confidence = self.langid.classify(text)
        return lang
    
    def fix_grammar(self, text, target_lang=None):
        if not target_lang:
            target_lang = self.detect_language(text)
        
        if target_lang == "sk":
            return self.fix_slovak(text)
        elif target_lang == "hr":
            return self.fix_croatian(text)
        elif target_lang == "en":
            return self.fix_english(text)
        return text
    
    def fix_slovak(self, text):
        corrections = {
            "somm": "som",
            "smu": "som", 
            "mam": "mám",
            "sa mas": "sa máš",
            "mas": "máś",
            "dakujem": "ďakujem",
            "dakujem": "ďakujem",
            "ahoj jak": "ahoj, ako",
            "ty si": "ty si",
            "ja som": "ja som",
            "sme": "sme",
            "ste": "ste",
            "su": "sú",
            "nie som": "nie som",
            "vsetko": "všetko",
            "dobre": "dobre",
            "ok": "ok",
            "super": "super",
            "majem": "mám",
            "máj": "mám",
            "sma": "som",
            "být": "byť",
            "pretože": "pretože",
            "takže": "takže",
            "lenže": "lenže",
            "ale": "ale",
            "mohlo": "mohlo",
            "budem": "budem",
            "môcť": "môcť",
            "skús": "skús",
            "znova": "znova",
            "čo": "čo",
            "najlepšie": "najlepšie",
            "môcť": "môcť",
            "po": "po",
            "tvojej": "tvojej",
            "strane": "strane",
            "tú": "tú",
            "životnú": "životnú",
            "úlohu": "úlohu",
            "prekvapivo": "prekvapivo",
            "šťastný": "šťastný",
            "podporujúci": "podporujúci",
            "dnes": "dnes",
            "pomôcť": "pomôcť",
        }
        
        result = text
        for wrong, correct in corrections.items():
            import re
            pattern = r'\b' + re.escape(wrong) + r'\b'
            result = re.sub(pattern, correct, result, flags=re.IGNORECASE)
        
        return result
    
    def fix_croatian(self, text):
        corrections = {
            "sem": "sam",
            "uvelike": "redu",
            "pravu smislu": "pravom smislu",
            "gotovo besprekidno": "gotovo besprekidno",
            "zdrava": "zdrava",
            "prijateljska": "prijateljska",
            "kako si danas": "kako si danas",
            "nek i": "neki",
            "suzvona": "zvona",
            "domovine": "domovine",
            "trebao": "trebao",
            "biti": "biti",
            "padnut": "pasti",
            "na lice": "na lice",
            "od sijete": "od sijete",
            "hudo": "u redu",
            "prijazno": "prijazno",
            "pričekam": "čekam",
            "naslednjo": "sljedeću",
            "razpravo": "razgovor",
            "kaj se zdi": "što se",
            "s strani": "s tvoje strane",
            "pošiljatelja": "pošiljatelja",
            " Bok ": " Bok ",
            " dobro ": " dobro ",
            " hvala ": " hvala ",
        }
        
        result = text
        for wrong, correct in corrections.items():
            import re
            pattern = r'\b' + re.escape(wrong) + r'\b'
            result = re.sub(pattern, correct, result, flags=re.IGNORECASE)
        
        return result
    
    def fix_english(self, text):
        return text
