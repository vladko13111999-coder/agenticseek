import os
import io
import re
import base64
import time
import numpy as np
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import httpx
import torch
from PIL import Image
from diffusers import StableDiffusionXLPipeline, DiffusionPipeline
import imageio

app = FastAPI(title="Brand Twin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tvojton.online",
        "https://www.tvojton.online",
        "http://localhost:3000",
        "http://localhost:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models (lazy loaded)
sdxl_pipe = None
video_pipe = None

def load_sdxl():
    global sdxl_pipe
    if sdxl_pipe is None:
        print("Loading SDXL Turbo model...")
        sdxl_pipe = StableDiffusionXLPipeline.from_pretrained(
            "stabilityai/sdxl-turbo",
            torch_dtype=torch.float16,
        )
        sdxl_pipe = sdxl_pipe.to("cuda")
        print("SDXL Turbo loaded!")
    return sdxl_pipe

def load_video():
    global video_pipe
    if video_pipe is None:
        print("Loading Zeroscope video model...")
        video_pipe = DiffusionPipeline.from_pretrained(
            "cerspense/zeroscope_v2_576w",
            torch_dtype=torch.float16,
        )
        video_pipe = video_pipe.to("cuda")
        print("Video model loaded!")
    return video_pipe

class QueryRequest(BaseModel):
    query: str


class ImageRequest(BaseModel):
    prompt: str


class VideoRequest(BaseModel):
    prompt: str


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

def detect_language(text: str) -> str:
    """Detect language - Slovak, Czech, Croatian, English"""
    text_lower = text.lower()
    
    sk_patterns = [
        (r'\b(viete|vies|neviete|nevis)\b', 3),
        (r'\b(čo|čoskoro|včera| zajtra)\b', 2),
        (r'\b(som|si|je|sme|ste|su)\b', 1),
        (r'\b(ake|aky|aká|aký)\b', 2),
        (r'\b(čau|ahojte|nazdar)\b', 1),
        (r'\b(povedz|povedzte|ukáž|ukážte)\b', 2),
        (r'\b(mám|máš|máme|máte|majú)\b', 2),
        (r'\b(ďakujem|vďaka|dakujem)\b', 2),
        (r'\b(potrebujem|chcem|chceš)\b', 2),
        (r'\b(generovať|vytvoriť|spraviť)\b', 2),
        (r'\b(slovensky|slovenčina)\b', 5),
    ]
    
    cs_patterns = [
        (r'\b(co|jak|proc|proč)\b', 2),
        (r'\b(jsem|jsi|jeho)\b', 1),
        (r'\b(dekuji|diky)\b', 2),
        (r'\b(chci|chtěl|chtěla)\b', 2),
        (r'\b(nevim|nevím)\b', 3),
        (r'\b(rekni|udelej)\b', 2),
    ]
    
    hr_patterns = [
        (r'\b(bok|cao|zivio)\b', 3),
        (r'\b(kako|što|gdje)\b', 2),
        (r'\b(hvala|lijepo)\b', 2),
    ]
    
    en_patterns = [
        (r'\b(hello|hi|hey)\b', 2),
        (r'\b(how|what|where|when|why)\b', 2),
        (r'\b(can you|could you|would you)\b', 3),
    ]
    
    scores = {'sk': 0, 'cs': 0, 'hr': 0, 'en': 0}
    
    for lang, patterns in [('sk', sk_patterns), ('cs', cs_patterns), ('hr', hr_patterns), ('en', en_patterns)]:
        for pattern, weight in patterns:
            if re.search(pattern, text_lower):
                scores[lang] += weight
    
    sk_only = 'áäčďéíľňóôšťúŕýžĺ'
    sk_diac = sum(1 for c in text if c.lower() in sk_only)
    scores['sk'] += sk_diac
    
    max_lang = max(scores, key=lambda k: scores[k])
    
    if scores[max_lang] < 2:
        return 'sk'
    
    return max_lang


def is_image_request(text: str) -> bool:
    """Check if user wants to generate an image"""
    text_lower = text.lower()
    image_keywords = [
        r'generuj.*obr[áa]zok', r'vygeneruj.*obr[áa]zok', r'sprav.*obr[áa]zok',
        r'vytvor.*obr[áa]zok', r'urob.*obr[áa]zok', r'nakresli',
        r'generate.*image', r'create.*image', r'make.*image', r'draw',
        r'obr[áa]zok.*z', r'image.*of', r'picture.*of',
        r'génère.*image', r'generiraj.*sliku', r'sliku',
    ]
    for kw in image_keywords:
        if re.search(kw, text_lower):
            return True
    return False


def is_video_request(text: str) -> bool:
    """Check if user wants to generate a video"""
    text_lower = text.lower()
    video_keywords = [
        r'generuj.*video', r'vygeneruj.*video', r'sprav.*video',
        r'vytvor.*video', r'urob.*video', r'animuj',
        r'generate.*video', r'create.*video', r'make.*video',
        r'video.*z', r'klip.*o',
    ]
    for kw in video_keywords:
        if re.search(kw, text_lower):
            return True
    return False


def extract_prompt(text: str) -> str:
    """Extract the prompt description from user text"""
    prefixes = [
        r'vygeneruj\s*', r'generuj\s*', r'sprav\s*', r'vytvor\s*',
        r'urob\s*', r'nakresli\s*', r'create\s*', r'make\s*',
        r'draw\s*', r'generate\s*', r'animuj\s*',
    ]
    
    result = text
    for prefix in prefixes:
        result = re.sub(prefix, '', result, flags=re.IGNORECASE)
    
    result = result.strip()
    if '?' in result:
        result = result.split('?')[0].strip()
    
    return result if result else text


@app.get("/health")
async def health():
    vram = 0
    if torch.cuda.is_available():
        vram = torch.cuda.memory_allocated() / 1e9
    return {
        "status": "healthy",
        "version": "1.1.0",
        "provider": "ollama",
        "sdxl_loaded": sdxl_pipe is not None,
        "vram_gb": round(vram, 2),
    }


@app.post("/query")
async def query(request: QueryRequest):
    try:
        lang = detect_language(request.query)
        
        # Check if this is a video request
        if is_video_request(request.query):
            video_prompt = extract_prompt(request.query)
            
            try:
                pipe = load_video()
                print(f"Generating video: {video_prompt}")
                
                video_frames = pipe(
                    prompt=video_prompt,
                    num_inference_steps=10,
                    height=256,
                    width=256,
                ).frames[0]
                
                # Convert frames to uint8
                frames_uint8 = [(frame * 255).astype(np.uint8) for frame in video_frames]
                
                # Save as GIF
                gif_buffer = io.BytesIO()
                imageio.mimsave(gif_buffer, frames_uint8, format='GIF', fps=8)
                gif_base64 = base64.b64encode(gif_buffer.getvalue()).decode()
                
                messages = {
                    'sk': 'Video bolo vygenerované!',
                    'cs': 'Video bylo vygenerováno!',
                    'hr': 'Video je izrađeno!',
                    'en': 'Video generated!',
                }
                
                return {
                    "done": "true",
                    "answer": messages.get(lang, messages['sk']),
                    "video_base64": gif_base64,
                    "prompt": video_prompt,
                    "agent_name": "TvojTon",
                    "success": "true",
                    "language": lang,
                    "blocks": {"video": gif_base64},
                    "status": "Ready",
                    "uid": "test-123",
                }
            except Exception as e:
                return {
                    "done": "true",
                    "answer": f"Nastala chyba pri generovaní videa: {str(e)}",
                    "agent_name": "TvojTon",
                    "success": "false",
                    "blocks": {},
                    "status": "Error",
                    "uid": "test-123",
                }
        
        # Check if this is an image request
        if is_image_request(request.query):
            image_prompt = extract_prompt(request.query)
            
            try:
                pipe = load_sdxl()
                print(f"Generating image: {image_prompt}")
                
                image = pipe(
                    prompt=image_prompt,
                    num_inference_steps=4,
                    guidance_scale=0.0,
                    height=512,
                    width=512
                ).images[0]
                
                # Convert to base64
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                img_base64 = base64.b64encode(buffer.getvalue()).decode()
                
                messages = {
                    'sk': 'Obrázok bol vygenerovaný!',
                    'cs': 'Obrázek byl vygenerován!',
                    'hr': 'Slika je izrađena!',
                    'en': 'Image generated!',
                }
                
                return {
                    "done": "true",
                    "answer": messages.get(lang, messages['sk']),
                    "image_base64": img_base64,
                    "prompt": image_prompt,
                    "agent_name": "TvojTon",
                    "success": "true",
                    "language": lang,
                    "blocks": {"image": img_base64},
                    "status": "Ready",
                    "uid": "test-123",
                }
            except Exception as e:
                return {
                    "done": "true",
                    "answer": f"Nastala chyba pri generovaní obrázka: {str(e)}",
                    "agent_name": "TvojTon",
                    "success": "false",
                    "blocks": {},
                    "status": "Error",
                    "uid": "test-123",
                }
        
        # Regular chat request
        lang = detect_language(request.query)
        
        system_prompts = {
            'sk': "SLOVAK ONLY. You MUST respond only in Slovak language. Never use Czech words. Response: Áno, viem po slovensky.",
            'cs': "CESKY ONLY. Odpovídej JEN česky.",
            'hr': "HRVATSKI ONLY. Odgovaraj SAMO hrvatski.",
            'en': "ENGLISH ONLY. Respond in English only."
        }
        
        system_msg = system_prompts.get(lang, system_prompts['sk'])
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": "gemma3:12b",
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": request.query}
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500,
                    }
                },
            )
            response.raise_for_status()
            result = response.json()
            answer = result.get("message", {}).get("content", "No response")
            return {
                "done": "true",
                "answer": answer.strip(),
                "reasoning": "",
                "agent_name": "TvojTon",
                "success": "true",
                "language": lang,
                "blocks": {},
                "status": "Ready",
                "uid": "test-123",
            }
    except httpx.HTTPError as e:
        return {
            "done": "true",
            "answer": f"Ospravedlňujem sa, mám technický problém.",
            "reasoning": "",
            "agent_name": "TvojTon",
            "success": "false",
            "blocks": {},
            "status": "Error",
            "uid": "test-123",
        }
    except Exception as e:
        return {
            "done": "true",
            "answer": f"Nastala neočakávaná chyba.",
            "reasoning": "",
            "agent_name": "TvojTon",
            "success": "false",
            "blocks": {},
            "status": "Error",
            "uid": "test-123",
        }


@app.post("/generate-image")
async def generate_image(request: ImageRequest):
    """Direct endpoint for image generation"""
    try:
        pipe = load_sdxl()
        print(f"Generating image: {request.prompt}")
        
        image = pipe(
            prompt=request.prompt,
            num_inference_steps=4,
            guidance_scale=0.0,
            height=512,
            width=512
        ).images[0]
        
        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "success": True,
            "image_base64": img_base64,
            "prompt": request.prompt,
            "model": "SDXL Turbo"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/generate-video")
async def generate_video(request: VideoRequest):
    """Direct endpoint for video generation"""
    try:
        pipe = load_video()
        print(f"Generating video: {request.prompt}")
        
        video_frames = pipe(
            prompt=request.prompt,
            num_inference_steps=10,
            height=256,
            width=256,
        ).frames[0]
        
        # Convert frames to uint8
        frames_uint8 = [(frame * 255).astype(np.uint8) for frame in video_frames]
        
        # Save as GIF
        gif_buffer = io.BytesIO()
        imageio.mimsave(gif_buffer, frames_uint8, format='GIF', fps=8)
        gif_base64 = base64.b64encode(gif_buffer.getvalue()).decode()
        
        return {
            "success": True,
            "video_base64": gif_base64,
            "prompt": request.prompt,
            "model": "Zeroscope v2",
            "frames": len(video_frames)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7777)
