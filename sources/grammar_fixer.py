import langid
import re

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
        # Czech to Slovak common corrections
        corrections = [
            (r'\bslepý\b', 'široký'),
            (r'\bslepej\b', 'slepý'),
            (r'\bslepé\b', 'široké'),
            (r'\bslepá\b', 'široká'),
            (r'\bmůže\b', 'môže'),
            (r'\bmůžete\b', 'môžete'),
            (r'\bmůžu\b', 'môžem'),
            (r'\bdobrý den\b', 'dobrý deň'),
            (r'\bčau\b', 'ahoj'),
            (r'\bčus\b', 'ahoj'),
            (r'\bco\b', 'čo'),
            (r'\bcos\b', 'čo si'),
            (r'\bcó\b', 'čo'),
            (r'\btakže\b', 'takže'),
            (r'\bjen\b', 'len'),
            (r'\bjeno\b', 'len'),
            (r'\bjsem\b', 'som'),
            (r'\bjsi\b', 'si'),
            (r'\bjsme\b', 'sme'),
            (r'\bsou\b', 'sú'),
            (r'\bmít\b', 'mať'),
            (r'\bmit\b', 'mať'),
            (r'\bbýt\b', 'byť'),
            (r'\bbit\b', 'byť'),
            (r'\bvidět\b', 'vidieť'),
            (r'\bříct\b', 'povedať'),
            (r'\brect\b', 'povedať'),
            (r'\bpřijít\b', 'prísť'),
            (r'\bzítra\b', ' zajtra'),
            (r'\bdneska\b', 'dnes'),
            (r'\bteď\b', 'teraz'),
            (r'\bpak\b', 'potom'),
            (r'\bkdyž\b', 'keď'),
            (r'\bprotože\b', 'pretože'),
            (r'\bprávě\b', 'práve'),
            (r'\bvlastně\b', 'vlastne'),
            (r'\bdoufám\b', 'dúfam'),
            (r'\bdík\b', 'vďaka'),
            (r'\bdíky\b', 'vďaka'),
            (r'\bdobře\b', 'dobre'),
            (r'\bpěkně\b', 'pekne'),
            (r'\bvidím\b', 'vidím'),
            (r'\bmyslím\b', 'myslím'),
            (r'\bvím\b', 'viem'),
            (r'\bchci\b', 'chcem'),
            (r'\bneumím\b', 'neviem'),
            (r'\bnevím\b', 'neviem'),
            (r'\bpřeji\b', 'želám'),
            (r'\bsnad\b', 'snáď'),
            (r'\bpořád\b', 'stále'),
            (r'\bvždycky\b', 'vždy'),
            (r'\bnikdy\b', 'nikdy'),
            (r'\bčasto\b', 'často'),
            (r'\bznovu\b', 'znova'),
            (r'\bzase\b', 'zasa'),
            (r'\bmám rád\b', 'mám rád'),
        ]
        
        result = text
        for pattern, replacement in corrections:
            try:
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            except:
                pass
        
        return result
    
    def fix_croatian(self, text):
        corrections = {
            "sem": "sam",
            "uvelike": "redu",
            "pričekam": "čekam",
            "naslednjo": "sljedeću",
            "razpravo": "razgovor",
        }
        
        result = text
        for wrong, correct in corrections.items():
            pattern = r'\b' + re.escape(wrong) + r'\b'
            result = re.sub(pattern, correct, result, flags=re.IGNORECASE)
        
        return result
    
    def fix_english(self, text):
        return text
