import langid
from transformers import MarianMTModel, MarianTokenizer
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

class LanguageUtility:
    def __init__(self, supported_language=[]):
        self.supported_language = supported_language
        self.models = {}
        self.tokenizers = {}
        self.load_models()

    def load_models(self):
        print("Načítavam prekladové modely Helsinki-NLP...")
        model_pairs = [
            ("en-sk", "Helsinki-NLP/opus-mt-en-sk"),
            ("sk-en", "Helsinki-NLP/opus-mt-sk-en"),
            ("en-hr", "Helsinki-NLP/opus-mt-en-hr"),
            ("hr-en", "Helsinki-NLP/opus-mt-hr-en"),
            ("en-zh", "Helsinki-NLP/opus-mt-en-zh"),
            ("zh-en", "Helsinki-NLP/opus-mt-zh-en"),
        ]
        
        for pair, model_name in model_pairs:
            try:
                print(f"  Loading {pair}: {model_name}")
                self.tokenizers[pair] = MarianTokenizer.from_pretrained(model_name)
                self.models[pair] = MarianMTModel.from_pretrained(model_name)
            except Exception as e:
                print(f"  Failed to load {pair}: {e}")
        
        print("✅ Prekladové modely pripravené")

    def detect_language(self, text):
        lang, confidence = langid.classify(text)
        return lang

    def _translate(self, text, source_lang, target_lang):
        """Translate text from source_lang to target_lang"""
        if source_lang == target_lang:
            return text
        
        pair = f"{source_lang}-{target_lang}"
        
        if pair not in self.models:
            return text
        
        model = self.models[pair]
        tokenizer = self.tokenizers[pair]
        
        if isinstance(text, list):
            text = " ".join(text)
            
        inputs = tokenizer(text, return_tensors="pt", padding=True)
        translated = model.generate(**inputs)
        result = tokenizer.decode(translated[0], skip_special_tokens=True)
        
        return result

    def translate_to_english(self, text, source_lang):
        """Preloží text z daného jazyka do angličtiny"""
        return self._translate(text, source_lang, "en")

    def translate_from_english(self, text, target_lang):
        """Preloží text z angličtiny do cieľového jazyka"""
        return self._translate(text, "en", target_lang)

    def translate(self, text, source_lang):
        """Pre router – preklad do angličtiny (aby sedelo volanie)"""
        return self.translate_to_english(text, source_lang)
