#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uuid
import asyncio
import time
import threading
import configparser
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Dict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import aiofiles
from dotenv import load_dotenv
import concurrent.futures

from sources.llm_provider import Provider
from sources.interaction import Interaction
from sources.agents import (
    CasualAgent,
    CoderAgent,
    FileAgent,
    PlannerAgent,
    BrowserAgent,
)
from sources.agent_router import AgentRouter
from sources.browser import Browser, create_driver
from web_browser import analyze_website
from sources.utility import pretty_print
from sources.logger import Logger
from sources.schemas import QueryRequest, QueryResponse
from brand_twin_api import setup_glm, generate_image
from video_generator import generate_video

load_dotenv()


def is_running_in_docker():
    return os.path.exists("/.dockerenv")


api = FastAPI(title="AgenticSeek API", version="0.1.0")
app = api  # pre kompatibilitu s existujúcimi endpointmi

# CORS middleware for Tvojton frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tvojton.online",
        "https://www.tvojton.online",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent router
agent_router = AgentRouter()

# Simple task queue
task_queue: Dict[str, dict] = {}
task_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def process_generate_task(task_id: str, url: str, lang: str):
    """Background task to process marketing generation"""
    global interaction, is_generating
    try:
        task_queue[task_id]["status"] = "processing"
        task_queue[task_id]["started_at"] = time.time()

        if interaction is None:
            task_queue[task_id]["status"] = "failed"
            task_queue[task_id]["error"] = "Agent initialization failed"
            return

        prompt = f"""Analyze the product from URL: {url}.
        Then create marketing materials in {lang} language:
        - Facebook ad (headline, primary text, CTA)
        - Instagram/TikTok post (text + hashtags)
        - SEO blog article (title, meta description, full article)
        - Competitor analysis (top 3 competitors, strengths & weaknesses)

        The marketing texts should be in {lang}, but you can think in English.
        Be creative and specific to the product."""

        async def run_task():
            global is_generating
            is_generating = True
            # Don't force translation since prompt already asks for target language
            success = await think_wrapper(interaction, prompt, force_lang=None)
            is_generating = False
            return success

        # Run async task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(run_task())
        finally:
            loop.close()

        if success:
            task_queue[task_id]["status"] = "completed"
            task_queue[task_id]["result"] = {
                "url": url,
                "language": lang,
                "answer": interaction.last_answer,
                "reasoning": interaction.last_reasoning,
                "success": interaction.last_success,
            }
        else:
            task_queue[task_id]["status"] = "failed"
            task_queue[task_id]["error"] = "Agent failed to process"
            task_queue[task_id]["answer"] = interaction.last_answer
    except Exception as e:
        task_queue[task_id]["status"] = "failed"
        task_queue[task_id]["error"] = str(e)
    finally:
        task_queue[task_id]["completed_at"] = time.time()


def process_video_task(task_id: str, url: str, lang: str, duration: int = 15):
    """Background task to generate video from product URL"""
    global interaction
    from sources.tools.web_analyzer import WebAnalyzer

    try:
        task_queue[task_id]["status"] = "analyzing"
        task_queue[task_id]["started_at"] = time.time()

        # Step 1: Analyze the product URL
        analyzer = WebAnalyzer()
        product_info = analyzer.execute(url)

        if "error" in product_info:
            task_queue[task_id]["status"] = "failed"
            task_queue[task_id]["error"] = (
                f"Failed to analyze URL: {product_info['error']}"
            )
            return

        task_queue[task_id]["status"] = "generating_script"
        task_queue[task_id]["product_info"] = product_info

        # Step 2: Generate video script using LLM
        prompt = f"""Create a short video advertisement script for a product.
        
Product name: {product_info.get("product_name", "Unknown")}
Description: {product_info.get("description", "")}
Price: {product_info.get("price", "")}

Create a {duration}-second video script in {lang} language.
Include:
- Hook (first 2 seconds)
- Product highlight (5 seconds)
- Call to action (last 3 seconds)

Keep it concise and engaging. Return ONLY the script text, nothing else."""

        if interaction is None:
            task_queue[task_id]["status"] = "failed"
            task_queue[task_id]["error"] = "Agent initialization failed"
            return

        async def run_video_task():
            global is_generating
            is_generating = True
            interaction.last_query = prompt
            await interaction.think()
            is_generating = False
            return interaction.last_answer

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            script = loop.run_until_complete(run_video_task())
        finally:
            loop.close()

        task_queue[task_id]["script"] = script

        # Step 3: Generate video (or create placeholder)
        task_queue[task_id]["status"] = "creating_video"

        output_dir = "static/videos"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{task_id}.mp4")

        if MOVIEPY_AVAILABLE:
            try:
                print(f"[DEBUG] Starting video generation for task {task_id}")
                print(
                    f"[DEBUG] Product: {product_info.get('product_name')}, Duration: {duration}s"
                )
                print(f"[DEBUG] Script: {script[:100]}...")

                # Font paths for Slovak diacritics - try multiple options
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                    "DejaVuSans-Bold",
                    "Arial",
                ]
                font_path = None
                for fp in font_paths:
                    if fp.startswith("/usr/share") and not os.path.exists(fp):
                        continue
                    font_path = fp
                    break

                if not font_path:
                    font_path = "DejaVuSans-Bold"

                print(f"[DEBUG] Using font: {font_path}")

                w, h = 1280, 720
                scenes = []

                # Parse script into scenes - ensure we have enough content
                script_lines = [
                    line.strip() for line in script.split("\n") if line.strip()
                ]

                # Ensure minimum number of scenes with fallback content
                if len(script_lines) < 2:
                    script_lines = [
                        product_info.get("product_name", "Produkt"),
                        script[:80] if script else "Vyskúšajte teraz!",
                        "Špeciálna ponuka pre vás",
                        "Kontaktujte nás",
                    ]

                # Ensure we have at least 4 lines for good video content
                while len(script_lines) < 4:
                    script_lines.append("Novinka!")

                # Create scene duration - divide total duration evenly
                num_scenes = min(len(script_lines), 4) + 2  # +2 for title and CTA
                scene_duration = max(1.5, duration / num_scenes)

                print(
                    f"[DEBUG] Creating {num_scenes} scenes, each {scene_duration:.1f}s"
                )

                # Scene 1: Title/Product name
                title = product_info.get("product_name", "Produkt")[:25]
                if not title or title == "Unknown":
                    title = "Náš Produkt"
                bg1 = ColorClip(
                    size=(w, h), color=(74, 144, 226), duration=scene_duration
                )
                txt1 = TextClip(
                    text=title,
                    font_size=60,
                    color="white",
                    font=font_path,
                    method="label",
                    duration=scene_duration,
                )
                txt1 = txt1.with_position(("center", "center"))
                scenes.append(CompositeVideoClip([bg1, txt1]))

                # Scene 2-4: Script lines as scenes (use up to 3 meaningful lines)
                colors = [(30, 64, 175), (124, 58, 237), (220, 38, 38), (34, 197, 94)]
                for i, line in enumerate(script_lines[1:4]):
                    if len(scenes) >= 5:  # Leave room for CTA
                        break
                    if not line or len(line) < 2:
                        continue
                    scene_bg = ColorClip(
                        size=(w, h),
                        color=colors[i % len(colors)],
                        duration=scene_duration,
                    )
                    txt = TextClip(
                        text=line[:50],  # Allow longer text
                        font_size=40,
                        color="white",
                        font=font_path,
                        method="label",
                        duration=scene_duration,
                    )
                    txt = txt.with_position(("center", "center"))
                    scenes.append(CompositeVideoClip([scene_bg, txt]))

                # Final scene: CTA with Slovak text
                cta_texts = [
                    "Kúpte teraz!",
                    "Objednajte teraz!",
                    "Vyskúšajte zadarmo!",
                    "Navštívte nás",
                ]
                cta_bg = ColorClip(
                    size=(w, h), color=(234, 179, 8), duration=scene_duration
                )
                cta_txt = TextClip(
                    text=cta_texts[0],
                    font_size=50,
                    color="black",
                    font=font_path,
                    method="label",
                    duration=scene_duration,
                )
                cta_txt = cta_txt.with_position(("center", "center"))
                scenes.append(CompositeVideoClip([cta_bg, cta_txt]))

                print(f"[DEBUG] Created {len(scenes)} scenes")

                # Concatenate all scenes
                if len(scenes) > 1:
                    from moviepy import concatenate_videoclips

                    video = concatenate_videoclips(scenes, method="compose")
                else:
                    video = scenes[0]

                print(f"[DEBUG] Writing video to {output_path}")
                video.write_videofile(output_path, fps=24, codec="libx264", audio=False)
                print(f"[DEBUG] Video saved successfully to {output_path}")
            except Exception as e:
                print(f"[DEBUG] Video generation failed: {str(e)}")
                import traceback

                traceback.print_exc()
                task_queue[task_id]["status"] = "failed"
                task_queue[task_id]["error"] = f"Video generation failed: {str(e)}"
                # Create placeholder file
                with open(output_path.replace(".mp4", ".txt"), "w") as f:
                    f.write(
                        f"Video script: {script}\n\nProduct: {product_info.get('product_name')}\nDuration: {duration}s"
                    )
                output_path = output_path.replace(".mp4", ".txt")
        else:
            # Create placeholder without moviepy
            with open(output_path.replace(".mp4", ".txt"), "w") as f:
                f.write(
                    f"Video script for {product_info.get('product_name')}:\n\n{script}\n\nDuration: {duration}s\nProduct URL: {url}"
                )
            output_path = output_path.replace(".mp4", ".txt")

        # Return result
        video_url = f"/static/videos/{os.path.basename(output_path)}"
        task_queue[task_id]["status"] = "completed"
        task_queue[task_id]["result"] = {
            "url": url,
            "language": lang,
            "duration": duration,
            "product_name": product_info.get("product_name"),
            "script": script,
            "video_url": video_url,
            "video_path": output_path,
        }

    except Exception as e:
        task_queue[task_id]["status"] = "failed"
        task_queue[task_id]["error"] = str(e)
    finally:
        task_queue[task_id]["completed_at"] = time.time()


from celery import Celery

celery_app = Celery(
    "tasks", broker="redis://localhost:6379/0", backend="redis://localhost:6379/0"
)
celery_app.conf.update(task_track_started=True)

# Video generation imports
try:
    import moviepy
    from moviepy import ColorClip, TextClip, CompositeVideoClip

    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

logger = Logger("backend.log")
config = configparser.ConfigParser()
config.read("config.ini")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Globálne premenné
interaction = None
is_generating = False
query_resp_history = []


# Inicializácia interakcie pri štarte
def init_interaction():
    global interaction
    print("Initializing interaction...")
    provider_name = config.get("MAIN", "provider_name")
    model_name = config.get("MAIN", "provider_model")
    raw_server = config.get(
        "MAIN", "provider_server_address", fallback="http://127.0.0.1:11434"
    )
    server_address = (
        raw_server.replace("http://", "").replace("https://", "").rstrip("/")
    )
    print(
        f"Using provider: {provider_name}, model: {model_name}, server: {server_address}"
    )
    provider = Provider(provider_name, model_name, server_address=server_address)

    # Vytvorenie prehliadača pre browser_agent (ak je dostupný)
    browser = None
    try:
        print("Creating browser driver...")
        driver = create_driver(headless=True)
        browser = Browser(driver)
    except Exception as e:
        print(
            f"Warning: Browser driver not available ({str(e)[:50]}). Browser agent will be disabled."
        )

    agents = {
        "planner": PlannerAgent(
            "planner", "prompts/planner_agent.txt", provider, verbose=False
        ),
        "coder": CoderAgent(
            "coder", "prompts/coder_agent.txt", provider, verbose=False
        ),
        "file": FileAgent("file", "prompts/file_agent.txt", provider, verbose=False),
        "casual": CasualAgent(
            "casual", "prompts/casual_agent.txt", provider, verbose=False
        ),
    }

    # Pridaj browser agent iba ak je browser dostupný
    if browser:
        agents["browser"] = BrowserAgent(
            "browser",
            "prompts/browser_agent.txt",
            provider,
            verbose=False,
            browser=browser,
        )
    print("Agents types:")
    for key, value in agents.items():
        print(f"  {key}: {type(value)}")
    interaction = Interaction(agents, tts_enabled=False, stt_enabled=False)
    if interaction is None:
        print(" FATAL: interaction is None after init!")
    else:
        print(" interaction initialized successfully.")


async def think_wrapper(interaction, query, force_lang=None):
    try:
        interaction.last_query = query
        logger.info("Agents request is being processed")
        success = await interaction.think(force_lang=force_lang)
        if not success:
            interaction.last_answer = "Error: No answer from agent"
            interaction.last_reasoning = "Error: No reasoning from agent"
            interaction.last_success = False
        else:
            interaction.last_success = True
        pretty_print(interaction.last_answer)
        interaction.speak_answer()
        return success
    except Exception as e:
        logger.error(f"Error in think_wrapper: {str(e)}")
        interaction.last_answer = ""
        interaction.last_reasoning = f"Error: {str(e)}"
        interaction.last_success = False
        raise e


@api.on_event("startup")
async def startup_event():
    logger.info("Startup event: initializing interaction...")
    init_interaction()  # toto je v poriadku, je odsadené vo vnútri funkcie


# koniec funkcie startup_event

# Endpointy

import os
from fastapi.responses import FileResponse


@api.get("/")
async def serve_frontend():
    html_path = "static/index.html"
    if os.path.exists(html_path):
        return FileResponse(html_path)
    else:
        return {"error": "Frontend file not found"}


@api.get("/screenshot")
async def get_screenshot():
    logger.info("Screenshot endpoint called")
    screenshot_path = ".screenshots/updated_screen.png"
    if os.path.exists(screenshot_path):
        return FileResponse(screenshot_path)
    logger.error("No screenshot available")
    return JSONResponse(status_code=404, content={"error": "No screenshot available"})


@api.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "healthy", "version": "0.1.0"}


@api.get("/is_active")
async def is_active():
    logger.info("Is active endpoint called")
    return {"is_active": interaction.is_active}


@api.get("/stop")
async def stop():
    logger.info("Stop endpoint called")
    interaction.current_agent.request_stop()
    return JSONResponse(status_code=200, content={"status": "stopped"})


@api.get("/latest_answer")
async def get_latest_answer():
    global query_resp_history
    if interaction.current_agent is None:
        return JSONResponse(status_code=404, content={"error": "No agent available"})
    uid = str(uuid.uuid4())
    if not any(
        q["answer"] == interaction.current_agent.last_answer for q in query_resp_history
    ):
        blocks = {}
        query_resp = {
            "done": "false",
            "answer": interaction.current_agent.last_answer,
            "reasoning": interaction.current_agent.last_reasoning,
            "agent_name": interaction.current_agent.agent_name
            if interaction.current_agent
            else "None",
            "success": interaction.current_agent.success,
            "blocks": blocks,
            "status": interaction.current_agent.get_status_message()
            if interaction.current_agent
            else "No agent",
            "uid": uid,
        }
        interaction.current_agent.last_answer = ""
        interaction.current_agent.last_reasoning = ""
        query_resp_history.append(query_resp)
        return JSONResponse(status_code=200, content=query_resp)
    if query_resp_history:
        return JSONResponse(status_code=200, content=query_resp_history[-1])
    return JSONResponse(status_code=404, content={"error": "No answer available"})


@api.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    global is_generating, query_resp_history, agent_router
    logger.info(f"Processing query: {request.query}")

    # Route the request
    agent_type, refined_query = agent_router.route(request.query)
    logger.info(f"Routed to: {agent_type}")

    # Handle image generation
    if agent_type == "image":
        img_result = generate_image(refined_query)
<<<<<<< Updated upstream
        return JSONResponse(status_code=200, content={
            "done": "true",
            "answer": img_result.get("message", "") + "\n\n" + img_result.get("prompt", ""),
            "reasoning": "",
            "agent_name": "GLM-Image",
            "success": str(img_result.get("success", True)),
            
            "image_base64": img_result.get("image_base64", "") if img_result else "",
            "status": "Ready",
            "uid": str(uuid.uuid4())
        })
    
    # Handle video generation
    if agent_type == "video":
        video_result = generate_video(refined_query)
        return JSONResponse(status_code=200, content={
            "done": "true",
            "answer": video_result.get("message", "") + "\n\nPrompt: " + video_result.get("prompt", refined_query),
            "reasoning": "",
            "agent_name": "Video-SVD",
            "success": str(video_result.get("success", False)),
            
            "status": "Ready",
            "uid": str(uuid.uuid4())
        })
    
    # Handle planner (placeholder)
    if agent_type == "planner":
        return JSONResponse(status_code=200, content={
            "done": "true",
            "answer": f"Planner request: {refined_query}\n\nPlanner agent will process this multi-step task.",
            "reasoning": "",
            "agent_name": "Planner",
            "success": "true",
            
            "status": "Ready",
            "uid": str(uuid.uuid4())
        })
    
=======
        return JSONResponse(
            status_code=200,
            content={
                "done": "true",
                "answer": img_result.get("message", "")
                + "\n\n"
                + img_result.get("prompt", ""),
                "reasoning": "",
                "agent_name": "GLM-Image",
                "success": str(img_result.get("success", True)),
                "blocks": {},
                "video_base64": video_result.get("video_base64", ""),
                "image_base64": img_result.get("image_base64", "")
                if img_result
                else "",
                "status": "Ready",
                "uid": str(uuid.uuid4()),
            },
        )

    # Handle video generation
    if agent_type == "video":
        video_result = generate_video(refined_query)
        return JSONResponse(
            status_code=200,
            content={
                "done": "true",
                "answer": video_result.get("message", "")
                + "\n\nPrompt: "
                + video_result.get("prompt", refined_query),
                "reasoning": "",
                "agent_name": "Video-SVD",
                "success": str(video_result.get("success", False)),
                "blocks": {},
                "video_base64": video_result.get("video_base64", ""),
                "status": "Ready",
                "uid": str(uuid.uuid4()),
            },
        )

    # Handle planner (placeholder)
    if agent_type == "planner":
        return JSONResponse(
            status_code=200,
            content={
                "done": "true",
                "answer": f"Planner request: {refined_query}\n\nPlanner agent will process this multi-step task.",
                "reasoning": "",
                "agent_name": "Planner",
                "success": "true",
                "blocks": {},
                "video_base64": video_result.get("video_base64", ""),
                "status": "Ready",
                "uid": str(uuid.uuid4()),
            },
        )

>>>>>>> Stashed changes
    # Continue with normal casual chat
    if is_generating:
        logger.warning("Another query is being processed, please wait.")
        return JSONResponse(
            status_code=429,
            content={"error": "Another query is being processed, please wait."},
        )
    try:
        is_generating = True

        # Detect language
        detected_lang = agent_router.detect_language(request.query)
        casual_agent = interaction.agents.get("casual")
        if casual_agent is None:
            casual_agent = interaction.current_agent

        interaction.last_query = request.query
        interaction.current_agent = casual_agent

        # Keep memory for conversation history - DO NOT clear
        # casual_agent.memory.clear() - REMOVED for conversation continuity

        # Process with detected language using the process method
        answer, reasoning = await casual_agent.process(
            request.query, None, force_lang=detected_lang
        )

        # Clean up any conversation tags from LLM response
        import re

        answer = re.sub(r"<\|user\|>.*?<\|assistant\|>", "", answer, flags=re.DOTALL)
        answer = re.sub(r"<\|user\|>", "", answer)
        answer = re.sub(r"<\|assistant\|>", "", answer)
        answer = answer.strip()

        # Remove repeating patterns - keep only unique lines
        lines = answer.split("\n")
        unique_lines = []
        seen_prefixes = set()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Get first 30 chars as key for deduplication
            prefix = line[:40].lower()
            if prefix not in seen_prefixes:
                seen_prefixes.add(prefix)
                unique_lines.append(line)
        answer = "\n".join(unique_lines[:3])  # Max 3 lines

        # If still too long, truncate at first sentence end
        if len(answer) > 300:
            # Find last sentence boundary
            last_period = answer[:300].rfind(". ")
            if last_period > 50:
                answer = answer[: last_period + 2]

        interaction.last_answer = answer
        interaction.last_reasoning = reasoning
        interaction.last_success = True

        # Save conversation memory
        casual_agent.memory.push("user", request.query)
        casual_agent.memory.push("assistant", answer)
        casual_agent.memory.save_memory("casual_agent")

        interaction.speak_answer()
        blocks = {}
        query_resp = QueryResponse(
            done="true",
            answer=interaction.last_answer,
            reasoning=interaction.last_reasoning,
            agent_name=interaction.current_agent.agent_name
            if interaction.current_agent
            else "Unknown",
            success=str(interaction.last_success),
            blocks=blocks,
            status="Ready",
            uid=str(uuid.uuid4()),
        )
        query_resp_dict = {
            "done": query_resp.done,
            "answer": query_resp.answer,
            "agent_name": query_resp.agent_name,
            "success": query_resp.success,
            "blocks": query_resp.blocks,
            "status": query_resp.status,
            "uid": query_resp.uid,
        }
        query_resp_history.append(query_resp_dict)
        logger.info("Query processed successfully")
        return JSONResponse(status_code=200, content=query_resp.jsonify())
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        is_generating = False
        if config.getboolean("MAIN", "save_session"):
            interaction.save_session()


@api.post("/generate")
async def generate(request: Request):
    global interaction
    if interaction is None:
        logger.warning("Interaction is None, re-initializing...")
        init_interaction()
        if interaction is None:
            return JSONResponse(
                status_code=500, content={"error": "Agent initialization failed."}
            )

    data = await request.json()
    url = data.get("url")
    lang = data.get("lang", "sk")

    if not url:
        return JSONResponse(status_code=400, content={"error": "URL is required"})

    # Create task ID
    task_id = str(uuid.uuid4())

    # Initialize task status
    task_queue[task_id] = {
        "status": "pending",
        "url": url,
        "lang": lang,
        "created_at": time.time(),
    }

    # Submit background task
    task_executor.submit(process_generate_task, task_id, url, lang)

    # Return immediately with task ID
    return JSONResponse(
        status_code=202,
        content={
            "task_id": task_id,
            "status": "pending",
            "message": "Task submitted. Use /status/{task_id} to check progress.",
        },
    )


@api.post("/generate_video")
async def video_generate_endpoint(request: Request):
    """Generate video from product URL"""
    global interaction
    if interaction is None:
        logger.warning("Interaction is None, re-initializing...")
        init_interaction()
        if interaction is None:
            return JSONResponse(
                status_code=500, content={"error": "Agent initialization failed."}
            )

    data = await request.json()
    url = data.get("url")
    lang = data.get("lang", "sk")
    duration = data.get("duration", 15)

    if not url:
        return JSONResponse(status_code=400, content={"error": "URL is required"})

    # Validate duration
    if duration not in [5, 10, 15, 30]:
        duration = 15

    # Create task ID
    task_id = str(uuid.uuid4())

    # Initialize task status
    task_queue[task_id] = {
        "status": "pending",
        "url": url,
        "lang": lang,
        "duration": duration,
        "created_at": time.time(),
    }

    # Submit background task
    task_executor.submit(process_video_task, task_id, url, lang, duration)

    # Return immediately with task ID
    return JSONResponse(
        status_code=202,
        content={
            "task_id": task_id,
            "status": "pending",
            "message": "Video generation started. Use /status/{task_id} to check progress.",
            "moviepy_available": MOVIEPY_AVAILABLE,
        },
    )


@api.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Check task status"""
    if task_id not in task_queue:
        return JSONResponse(status_code=404, content={"error": "Task not found"})

    task = task_queue[task_id]
    response = {
        "task_id": task_id,
        "status": task["status"],
        "created_at": task.get("created_at"),
    }

    if task["status"] == "completed":
        response["result"] = task.get("result")
    elif task["status"] == "failed":
        response["error"] = task.get("error", "Unknown error")
        response["answer"] = task.get("answer")

    return JSONResponse(status_code=200, content=response)


# Obsluha statických súborov
api.mount("/static", StaticFiles(directory="static"), name="static")


@api.post("/route")
async def route_request(request: Request):
    """Route a user request to the appropriate agent."""
    global agent_router
    data = await request.json()
    query = data.get("query", "")

    if not query:
        return JSONResponse(status_code=400, content={"error": "Query is required"})

    agent_type, refined_query = agent_router.route(query)
    detected_lang = agent_router.detect_language(query)

    return JSONResponse(
        status_code=200,
        content={
            "original_query": query,
            "detected_language": detected_lang,
            "agent_type": agent_type,
            "refined_query": refined_query,
            "available_agents": ["casual", "image", "video", "planner"],
        },
    )


@api.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn

    if is_running_in_docker():
        print("[AgenticSeek] Starting in Docker container...")
    else:
        print("[AgenticSeek] Starting on host machine...")
    envport = os.getenv("BACKEND_PORT")
    port = int(envport) if envport else 7777
    uvicorn.run(api, host="0.0.0.0", port=port)
