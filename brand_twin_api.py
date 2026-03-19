"""
Brand Twin API - Image Generation with AI prompt enhancement
Uses Ollama for text generation (lightweight)
"""
import os
from typing import Dict, Any
import ollama
import logging

logger = logging.getLogger(__name__)

class ImageGenerator:
    """Image generation prompt enhancer using Ollama"""
    
    def __init__(self):
        self.model = "gams3:12b"
        self.loaded = True  # Ollama is always ready
    
    def create_image_prompt(self, user_request: str) -> str:
        """Create enhanced image generation prompt"""
        prompt = f"""Create a detailed AI image generation prompt.
Subject: {user_request}

Rules:
- Describe the main subject clearly
- Add artistic style (realistic, anime, abstract, etc.)
- Include lighting (sunset, studio, dramatic, soft, etc.)
- Specify colors and mood
- Add composition details

Respond ONLY with the enhanced prompt in Slovak or English, nothing else."""

        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.8, "max_tokens": 200}
            )
            return response['response'].strip()
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return f"A detailed image of {user_request} with vibrant colors and professional lighting"

img_gen = ImageGenerator()

def setup_glm():
    """Check if Ollama is available"""
    try:
        ollama.list()
        return True
    except:
        return False

def generate_image(prompt: str) -> Dict[str, Any]:
    """Generate enhanced image prompt"""
    try:
        enhanced = img_gen.create_image_prompt(prompt)
        return {
            "success": True,
            "type": "image_generation",
            "prompt": enhanced,
            "message": "Tu je vygenerovaný prompt pre AI obrázok:",
            "model": "ImageGen (Ollama/gams3:12b)"
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Ospravedlňujem sa, pri generovaní došlo k chybe."
        }
