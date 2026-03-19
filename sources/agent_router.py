"""
Agent Router - routes user requests to the appropriate agent
"""
import re
from typing import Tuple, Optional

class AgentRouter:
    """
    Routes user requests to the appropriate agent based on keywords.
    
    Agents:
    - casual: General chat, greetings, simple questions
    - image: Image generation requests
    - video: Video generation requests
    - planner: Complex multi-step tasks
    """
    
    # Keywords for each agent type
    IMAGE_KEYWORDS = [
        r'vygeneruj.*obr[áa]zok', r'sprav.*obr[áa]zok', r'urob.*thumbnail',
        r'generate.*image', r'create.*picture', r'nakresli', r'namaluj',
        r'make.*image', r'draw', r'paint', r'vytvor.*obr[áa]zok',
        r'generate.*photo', r'create.*art', r'design.*image',
        r'obr[áa]zok.*z', r'picture.*of', r'génère.*image',
        r'generiraj.*sliku', r'sliku', r'generisi'
    ]
    
    VIDEO_KEYWORDS = [
        r'sprav.*video', r'vygeneruj.*video', r'vytvor.*klip',
        r'make.*video', r'generate.*clip', r'animuj',
        r'video.*z', r'klip.*o', r'shot.*video', r'movie',
        r'generiraj.*video', r'napravi.*video',
        r'animiraj', r'create.*animation', r'generuj.*animac'
    ]
    
    PLANNER_KEYWORDS = [
        r'n[áa]jdi.*a', r'n[áa]jdi.*recept', r'n[áa]jdi.*inform',
        r'vyh[ľl]adaj.*a', r'vyh[ľl]adaj.*a.*zhr[ňn]', r'vyh[ľl]adaj.*a.*shr[ňn]',
        r'find.*and', r'and.*summarize', r'and.*read', r'and.*explain',
        r'research', r'analyze', r'vyhľadaj.*recept.*nahlas',
        r'viac.*krokov', r'multiple.*steps', r'complex.*task',
        r'nájdi.*a.*sprav', r'vyhľadaj.*a.*vysvetli',
        r'pretraž', r'pronađi.*i.*pročitaj', r'pronađi.*i.*sazmi',
        r'istraži', r'pretraži', r'hľadaj.*a'
    ]
    
    def __init__(self):
        """Initialize the router with compiled regex patterns."""
        self.image_patterns = [re.compile(k, re.IGNORECASE) for k in self.IMAGE_KEYWORDS]
        self.video_patterns = [re.compile(k, re.IGNORECASE) for k in self.VIDEO_KEYWORDS]
        self.planner_patterns = [re.compile(k, re.IGNORECASE) for k in self.PLANNER_KEYWORDS]
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the input text."""
        text_lower = text.lower()
        
        # Slovak indicators
        sk_words = ['ahoj', 'Ďakujem', ' Dakujem', 'som', 'máš', 'mám', 'ako', 'čo', 'kto', 'kde', 'pretože', 'že']
        # English indicators  
        en_words = ['hello', 'hi', 'thanks', 'thank', 'how are', 'what', 'where', 'because', 'the', 'is', 'are']
        # Croatian indicators
        hr_words = ['bok', 'hvala', 'kako', 'što', 'gdje', 'jer', 'jesi', 'jesam', 'dobro', 'lijepo']
        
        sk_count = sum(1 for w in sk_words if w in text_lower)
        en_count = sum(1 for w in en_words if w in text_lower)
        hr_count = sum(1 for w in hr_words if w in text_lower)
        
        if sk_count >= en_count and sk_count >= hr_count:
            return 'sk'
        elif hr_count >= en_count:
            return 'hr'
        else:
            return 'en'
    
    def route(self, user_input: str) -> Tuple[str, str]:
        """
        Route the user input to the appropriate agent.
        
        Args:
            user_input: The user's message
            
        Returns:
            Tuple of (agent_type, refined_prompt)
            agent_type: 'casual', 'image', 'video', or 'planner'
        """
        # Check for IMAGE request
        for pattern in self.image_patterns:
            if pattern.search(user_input):
                refined = self._refine_image_prompt(user_input)
                return 'image', refined
        
        # Check for VIDEO request
        for pattern in self.video_patterns:
            if pattern.search(user_input):
                refined = self._refine_video_prompt(user_input)
                return 'video', refined
        
        # Check for PLANNER request
        for pattern in self.planner_patterns:
            if pattern.search(user_input):
                refined = self._refine_planner_prompt(user_input)
                return 'planner', refined
        
        # Default to CASUAL (chat)
        return 'casual', user_input
    
    def _refine_image_prompt(self, prompt: str) -> str:
        """Refine the prompt for image generation."""
        # Remove common prefixes
        prefixes = [
            r'^vygeneruj\s*', r'^sprav\s*', r'^urob\s*', r'^vytvor\s*',
            r'^generate\s*', r'^create\s*', r'^make\s*', r'^draw\s*',
            r'^namaluj\s*', r'^nakresli\s*', r'^generiraj\s*', r'^sliku\s*'
        ]
        result = prompt
        for prefix in prefixes:
            result = re.sub(prefix, '', result, flags=re.IGNORECASE)
        return result.strip()
    
    def _refine_video_prompt(self, prompt: str) -> str:
        """Refine the prompt for video generation."""
        prefixes = [
            r'^sprav\s*', r'^vygeneruj\s*', r'^vytvor\s*', r'^animuj\s*',
            r'^make\s*', r'^generate\s*', r'^create\s*', r'^animiraj\s*',
            r'^generiraj\s*', r'^napravi\s*'
        ]
        result = prompt
        for prefix in prefixes:
            result = re.sub(prefix, '', result, flags=re.IGNORECASE)
        return result.strip()
    
    def _refine_planner_prompt(self, prompt: str) -> str:
        """Refine the prompt for planner agent."""
        return prompt


def route_request(user_input: str) -> Tuple[str, str]:
    """
    Convenience function to route a request.
    
    Args:
        user_input: The user's message
        
    Returns:
        Tuple of (agent_type, refined_prompt)
    """
    router = AgentRouter()
    return router.route(user_input)


if __name__ == "__main__":
    # Test the router
    router = AgentRouter()
    
    test_cases = [
        "Ahoj! Ako sa máš?",
        "vygeneruj obrázok západu slnka",
        "sprav video mačky",
        "nájdi recept na koláče a prečítaj ho nahlas",
        "Hello! How are you?",
        "generate image of a cat",
        "make a video of dogs playing",
        "find and summarize the news",
        "Bok! Kako si?",
        "generiraj sliku planine"
    ]
    
    print("Agent Router Test")
    print("=" * 60)
    
    for test in test_cases:
        agent_type, refined = router.route(test)
        lang = router.detect_language(test)
        print(f"Input: {test}")
        print(f"  → Language: {lang}")
        print(f"  → Agent: {agent_type}")
        print(f"  → Refined: {refined}")
        print()
