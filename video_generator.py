import os
import io
import base64
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class VideoGen:
    def __init__(self):
        self.model = None
        self.pipeline = None
        self.model_loaded = False
        self.model_type = None
    
    def load_model(self, model_type="svd"):
        if self.model_loaded and self.model_type == model_type:
            return True
        try:
            if model_type == "svd":
                from diffusers import StableVideoDiffusionPipeline
                import torch
                logger.info("Loading Stable Video Diffusion model...")
                self.pipeline = StableVideoDiffusionPipeline.from_pretrained(
                    "stabilityai/stable-video-diffusion-img2vid-xt",
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    local_files_only=False
                )
                if torch.cuda.is_available():
                    self.pipeline = self.pipeline.to("cuda")
                self.model_type = "svd"
                self.model_loaded = True
                logger.info("SVD model loaded!")
                return True
        except Exception as e:
            logger.error(f"Error loading video model: {e}")
            return False
    
    def generate_from_image(self, image, prompt="") -> Optional[bytes]:
        if not self.load_model("svd"):
            return None
        try:
            from PIL import Image
            if isinstance(image, str):
                image = Image.open(image).convert("RGB")
            image = image.resize((1024, 576))
            logger.info("Generating video from image...")
            frames = self.pipeline(image, decode_chunk_size=8, num_frames=25, max_guidance_scale=3.0).frames[0]
            output_path = "/workspace/videos/video_{}.mp4".format(int(time.time()))
            os.makedirs("/workspace/videos", exist_ok=True)
            import imageio
            imageio.mimsave(output_path, frames, fps=8)
            with open(output_path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Video generation error: {e}")
            return None

video_gen = VideoGen()

def generate_video(prompt: str, image_base64: str = None) -> Dict[str, Any]:
    try:
        os.makedirs("/workspace/videos", exist_ok=True)
        if image_base64:
            from PIL import Image
            img_data = base64.b64decode(image_base64)
            img = Image.open(io.BytesIO(img_data))
            video_bytes = video_gen.generate_from_image(img, prompt)
            if video_bytes:
                video_b64 = base64.b64encode(video_bytes).decode()
                return {
                    "success": True,
                    "type": "video_generation",
                    "prompt": prompt,
                    "video_base64": video_b64,
                    "message": "Video bolo vygenerovane!",
                    "model": "Stable Video Diffusion XT"
                }
        return {
            "success": True,
            "type": "video_generation",
            "prompt": prompt,
            "message": "Video generovanie je pripravene. Pridaj obrazok pre generovanie videa.",
            "model": "Stable Video Diffusion XT"
        }
    except Exception as e:
        logger.error(f"Video generation error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Pri generovani videa doslo k chybe."
        }
