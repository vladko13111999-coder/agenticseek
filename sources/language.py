import langid
from transformers import MarianMTModel, MarianTokenizer, M2M100ForConditionalGeneration, M2M100Tokenizer
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

class LanguageUtility:
    def __init__(self, supported_language=[]):
        self.supported_language = supported_language
        self.models = {}
        self.tokenizers = {}
        self.m2m_model = None
        self.m2m_tokenizer = None
        self.load_models()

    def load_models(self):
        print("Načítavam prekladové modely Helsinki-NLP...")
        model_pairs = [
            ("en-sk", "Helsinki-NLP/opus-mt-en-sk"),
            ("sk-en", "Helsinki-NLP/opus-mt-sk-en"),
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
        
        print("  Loading M2M100 for Croatian...")
        try:
            self.m2m_tokenizer = M2M100Tokenizer.from_pretrained("facebook/m2m100_418M")
            self.m2m_model = M2M100ForConditionalGeneration.from_pretrained("facebook/m2m100_418M")
            print("  ✅ M2M100 loaded for hr↔en")
        except Exception as e:
            print(f"  Failed to load M2M100: {e}")
        
        print("✅ Prekladové modely pripravené")

    def detect_language(self, text):
        lang, confidence = langid.classify(text)
        return lang

    def _translate_m2m(self, text, source_lang, target_lang):
        """Translate using M2M100 model"""
        if not self.m2m_model or not self.m2m_tokenizer:
            return text
        
        self.m2m_tokenizer.src_lang = source_lang
        encoded = self.m2m_tokenizer(text, return_tensors="pt")
        generated_tokens = self.m2m_model.generate(
            **encoded,
            forced_bos_token_id=self.m2m_tokenizer.get_lang_id(target_lang)
        )
        translated = self.m2m_tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
        return translated

    def _translate(self, text, source_lang, target_lang):
        """Translate text from source_lang to target_lang"""
        if source_lang == target_lang:
            return text
        
        if source_lang == "hr" or target_lang == "hr":
            return self._translate_m2m(text, source_lang, target_lang)
        
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
