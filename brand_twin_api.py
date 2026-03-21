"""
Brand Twin API - Image and Video Generation
Uses Ollama for text enhancement and local models for generation
"""
import os
import io
import base64
import logging
from typing import Dict, Any
import ollama
from PIL import Image
import torch

logger = logging.getLogger(__name__)

class ImageGenerator:
    """Image generation with Ollama prompt enhancement"""
    
    def __init__(self):
        self.model = "qwen2.5:14b"  # Use qwen for better prompt enhancement
        self.image_model = None  # Will be loaded on demand
        self.loaded = True
    
    def create_image_prompt(self, user_request: str) -> str:
        """Create enhanced image generation prompt"""
        prompt = f"""Create a detailed AI image generation prompt for: {user_request}

Rules:
- Start with the main subject description
- Add artistic style (realistic, anime, abstract, photography, etc.)
- Include lighting details (natural, studio, dramatic, soft, golden hour, etc.)
- Specify color palette and mood
- Add composition (portrait, landscape, close-up, wide shot)
- Include quality tags: masterpiece, best quality, detailed

Respond ONLY with the enhanced prompt, nothing else. Maximum 200 characters."""

        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.7, "num_predict": 150}
            )
            enhanced = response['response'].strip()
            # Ensure it's not too long
            if len(enhanced) > 200:
                enhanced = enhanced[:200]
            return enhanced
        except Exception as e:
            logger.error(f"Ollama prompt enhancement error: {e}")
            return f"detailed photo of {user_request}, professional lighting, high quality, masterpiece"

    def generate_with_stable_diffusion(self, prompt: str, output_dir: str = "/workspace/images") -> Dict[str, Any]:
        """Generate image using Stable Diffusion (if available)"""
        try:
            from diffusers import StableDiffusionPipeline
            import torch
            
            os.makedirs(output_dir, exist_ok=True)
            
            # Load model on first use
            if self.image_model is None:
                logger.info("Loading Stable Diffusion model...")
                # Use a smaller model for faster loading
                self.image_model = StableDiffusionPipeline.from_pretrained(
                    "runwayml/stable-diffusion-v1-5",
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    safety_checker=None,
                    requires_safety_checker=False
                )
                if torch.cuda.is_available():
                    self.image_model = self.image_model.to("cuda")
                logger.info("Stable Diffusion model loaded!")
            
            # Generate image
            image = self.image_model(
                prompt=prompt,
                num_inference_steps=25,
                guidance_scale=7.5,
                height=512,
                width=512
            ).images[0]
            
            # Save image
            import time
            filename = f"image_{int(time.time())}.png"
            filepath = os.path.join(output_dir, filename)
            image.save(filepath)
            
            # Convert to base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            return {
                "success": True,
                "type": "image_generation",
                "prompt": prompt,
                "image_url": f"/workspace/images/{filename}",
                "image_base64": img_base64,
                "message": "Obrázok bol úspešne vygenerovaný!",
                "model": "Stable Diffusion 1.5"
            }
        except ImportError as e:
            logger.warning(f"Diffusers not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return None


class VideoGenerator:
    """Video generation placeholder for LTX-Video"""
    
    def __init__(self):
        self.model = "ltx-video"  # LTX-Video model
        self.loaded = False
    
    def generate_video(self, prompt: str) -> Dict[str, Any]:
        """Generate video (placeholder - LTX-Video integration pending)"""
        return {
            "success": False,
            "type": "video_generation",
            "prompt": prompt,
            "message": "Generovanie videí bude čoskoro dostupné! LTX-Video sa pripravuje.",
            "model": "LTX-Video (pending)"
        }


# Initialize generators
img_gen = ImageGenerator()
video_gen = VideoGenerator()


def setup_glm():
    """Check if Ollama is available"""
    try:
        ollama.list()
        return True
    except:
        return False


def generate_image(prompt: str) -> Dict[str, Any]:
    """Generate image from text prompt"""
    try:
        # First, enhance the prompt using Ollama
        enhanced_prompt = img_gen.create_image_prompt(prompt)
        
        # Try to generate actual image with Stable Diffusion
        sd_result = img_gen.generate_with_stable_diffusion(enhanced_prompt)
        
        if sd_result and sd_result.get("success"):
            return sd_result
        
        # Fallback: return enhanced prompt if SD not available
        return {
            "success": True,
            "type": "image_generation",
            "prompt": enhanced_prompt,
            "message": f"Prompt pre generovanie obrázka:\n\n{enhanced_prompt}\n\n⚠️ Poznámka: Pre skutočné generovanie obrázkov je potrebné nainštalovať Stable Diffusion model.",
            "model": "GLM-Image (Ollama/qwen2.5:14b)"
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Ospravedlňujem sa, pri generovaní obrázka došlo k chybe."
        }


def generate_video(prompt: str) -> Dict[str, Any]:
    """Generate video from text prompt"""
    return video_gen.generate_video(prompt)
