#!/usr/bin/env python3

import os
import sys
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
from sources.agents import CasualAgent, CoderAgent, FileAgent, PlannerAgent, BrowserAgent
from sources.browser import Browser, create_driver
from sources.utility import pretty_print
from sources.logger import Logger
from sources.schemas import QueryRequest, QueryResponse

load_dotenv()

def is_running_in_docker():
    return os.path.exists('/.dockerenv')

api = FastAPI(title="AgenticSeek API", version="0.1.0")
app = api  # pre kompatibilitu s existujúcimi endpointmi

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
                "success": interaction.last_success
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

# Celery (nepoužíva sa zatiaľ, ale môžeš nechať)
from celery import Celery
celery_app = Celery("tasks", broker="redis://localhost:6379/0", backend="redis://localhost:6379/0")
celery_app.conf.update(task_track_started=True)

logger = Logger("backend.log")
config = configparser.ConfigParser()
config.read('config.ini')

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
    provider_name = config.get('MAIN', 'provider_name')
    model_name = config.get('MAIN', 'provider_model')
    raw_server = config.get('MAIN', 'provider_server_address', fallback='http://127.0.0.1:11434')
    server_address = raw_server.replace('http://', '').replace('https://', '').rstrip('/')
    print(f"Using provider: {provider_name}, model: {model_name}, server: {server_address}")
    provider = Provider(provider_name, model_name, server_address=server_address)

    # Vytvorenie prehliadača pre browser_agent
    print("Creating browser driver...")
    driver = create_driver(headless=True)
    browser = Browser(driver)
    agents = {
        "planner": PlannerAgent("planner", "prompts/planner_agent.txt", provider, verbose=False),
        "coder": CoderAgent("coder", "prompts/coder_agent.txt", provider, verbose=False),
        "file": FileAgent("file", "prompts/file_agent.txt", provider, verbose=False),
        "browser": BrowserAgent("browser", "prompts/browser_agent.txt", provider, verbose=False, browser=browser),
        "casual": CasualAgent("casual", "prompts/casual_agent.txt", provider, verbose=False)
    }
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
    init_interaction()   # toto je v poriadku, je odsadené vo vnútri funkcie

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
    if not any(q["answer"] == interaction.current_agent.last_answer for q in query_resp_history):
        blocks = {f'{i}': block.jsonify() for i, block in enumerate(interaction.get_last_blocks_results())}
        query_resp = {
            "done": "false",
            "answer": interaction.current_agent.last_answer,
            "reasoning": interaction.current_agent.last_reasoning,
            "agent_name": interaction.current_agent.agent_name if interaction.current_agent else "None",
            "success": interaction.current_agent.success,
            "blocks": blocks,
            "status": interaction.current_agent.get_status_message() if interaction.current_agent else "No agent",
            "uid": uid
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
    global is_generating, query_resp_history
    logger.info(f"Processing query: {request.query}")
    if is_generating:
        logger.warning("Another query is being processed, please wait.")
        return JSONResponse(status_code=429, content={"error": "Another query is being processed, please wait."})
    try:
        is_generating = True
        success = await think_wrapper(interaction, request.query)
        if not success:
            return JSONResponse(status_code=400, content={
                "answer": interaction.last_answer,
                "reasoning": interaction.last_reasoning,
                "success": False
            })
        if interaction.current_agent:
            blocks = {f'{i}': block.jsonify() for i, block in enumerate(interaction.current_agent.get_blocks_results())}
        else:
            blocks = {}
        query_resp = QueryResponse(
            done="true",
            answer=interaction.last_answer,
            reasoning=interaction.last_reasoning,
            agent_name=interaction.current_agent.agent_name if interaction.current_agent else "Unknown",
            success=str(interaction.last_success),
            blocks=blocks,
            status="Ready",
            uid=str(uuid.uuid4())
        )
        query_resp_dict = {
            "done": query_resp.done,
            "answer": query_resp.answer,
            "agent_name": query_resp.agent_name,
            "success": query_resp.success,
            "blocks": query_resp.blocks,
            "status": query_resp.status,
            "uid": query_resp.uid
        }
        query_resp_history.append(query_resp_dict)
        logger.info("Query processed successfully")
        return JSONResponse(status_code=200, content=query_resp.jsonify())
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        is_generating = False
        if config.getboolean('MAIN', 'save_session'):
            interaction.save_session()
@api.post("/generate")
async def generate(request: Request):
    global interaction
    if interaction is None:
        logger.warning("Interaction is None, re-initializing...")
        init_interaction()
        if interaction is None:
            return JSONResponse(status_code=500, content={"error": "Agent initialization failed."})

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
        "created_at": time.time()
    }
    
    # Submit background task
    task_executor.submit(process_generate_task, task_id, url, lang)
    
    # Return immediately with task ID
    return JSONResponse(status_code=202, content={
        "task_id": task_id,
        "status": "pending",
        "message": "Task submitted. Use /status/{task_id} to check progress."
    })

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
