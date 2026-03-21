import os
import io
import base64
import logging
import time
import json
from typing import Dict, Any
import ollama
from PIL import Image
import torch
from diffusers import StableDiffusionPipeline

logger = logging.getLogger(__name__)

class ImageGenerator:
    def __init__(self):
        self.model = "qwen2.5:14b"
        self.sd_pipeline = None
        self.sd_loaded = False
    
    def create_image_prompt(self, user_request: str) -> str:
        prompt = f"""Create a detailed AI image generation prompt for: {user_request}
Rules:
- Start with the main subject description
- Add artistic style realistic anime abstract photography etc
- Include lighting details natural studio dramatic soft golden hour
- Specify color palette and mood
- Add composition portrait landscape close-up wide shot
- Include quality tags masterpiece best quality detailed
Respond ONLY with the enhanced prompt. Maximum 200 characters."""
        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.7, "num_predict": 150}
            )
            enhanced = response['response'].strip()
            if len(enhanced) > 200:
                enhanced = enhanced[:200]
            return enhanced
        except Exception as e:
            logger.error(f"Ollama prompt enhancement error: {e}")
            return f"detailed photo of {user_request}, professional lighting, high quality, masterpiece"
    
    def load_sd_model(self):
        if self.sd_loaded:
            return True
        try:
            logger.info("Loading Stable Diffusion model...")
            self.sd_pipeline = StableDiffusionPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                safety_checker=None,
                requires_safety_checker=False
            )
            if torch.cuda.is_available():
                self.sd_pipeline = self.sd_pipeline.to("cuda")
            self.sd_loaded = True
            logger.info("Stable Diffusion model loaded!")
            return True
        except Exception as e:
            logger.error(f"SD loading error: {e}")
            return False
    
    def generate_with_sd(self, prompt: str) -> Dict[str, Any]:
        try:
            if not self.load_sd_model():
                return None
            
            logger.info(f"Generating image with SD: {prompt[:50]}...")
            image = self.sd_pipeline(
                prompt=prompt,
                num_inference_steps=25,
                guidance_scale=7.5,
                height=512,
                width=512
            ).images[0]
            
            os.makedirs("/workspace/images", exist_ok=True)
            filename = f"image_{int(time.time())}.png"
            filepath = f"/workspace/images/{filename}"
            image.save(filepath)
            
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            return {
                "success": True,
                "type": "image_generation",
                "prompt": prompt,
                "image_path": filepath,
                "image_base64": img_base64,
                "message": "Obrázok bol vygenerovaný!",
                "model": "Stable Diffusion 1.5"
            }
        except Exception as e:
            logger.error(f"SD generation error: {e}")
            return None


class VideoGenerator:
    def __init__(self):
        self.model = "x/flux2-klein"
        self.flux_available = True
    
    def generate_video(self, prompt: str) -> Dict[str, Any]:
        return {
            "success": True,
            "type": "video_generation",
            "prompt": prompt,
            "message": "Video generovanie je v priprave. FLUX.2 Klein model je nainstalovany.",
            "model": "FLUX.2 Klein (pending integration)",
            "status": "coming_soon"
        }


img_gen = ImageGenerator()
video_gen = VideoGenerator()


def setup_glm():
    try:
        ollama.list()
        return True
    except:
        return False


def generate_image(prompt: str) -> Dict[str, Any]:
    try:
        enhanced_prompt = img_gen.create_image_prompt(prompt)
        
        sd_result = img_gen.generate_with_sd(enhanced_prompt)
        
        if sd_result and sd_result.get("success"):
            return sd_result
        
        return {
            "success": True,
            "type": "image_generation",
            "prompt": enhanced_prompt,
            "message": f"Prompt pre generovanie:\n\n{enhanced_prompt}",
            "model": "Stable Diffusion 1.5"
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Pri generovani obrazka doslo k chybe."
        }


def generate_video(prompt: str) -> Dict[str, Any]:
    return video_gen.generate_video(prompt)
