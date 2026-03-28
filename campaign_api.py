import os
import json
import asyncio
import threading
import time
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from campaign import (
    start_campaign, run_campaign_step, check_lead_response,
    search_and_import_leads, get_campaign_status, list_campaigns,
    load_campaign, save_campaign, Campaign,
    send_daily_report, generate_daily_report, make_call, send_sms
)

app = FastAPI(title="Tvojton AI - Campaign API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StartCampaignRequest(BaseModel):
    target_segment: str
    monthly_limit: int = 50
    daily_limit: int = 10
    calls_enabled: bool = False

class SearchLeadsRequest(BaseModel):
    query: Optional[str] = None

class LeadResponseRequest(BaseModel):
    lead_url: str
    response_text: str

class MakeCallRequest(BaseModel):
    phone: str
    script: str

class SendSmsRequest(BaseModel):
    phone: str
    message: str

@app.get("/")
async def root():
    return {"service": "Tvojton Campaign API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "campaign"}

@app.post("/start_campaign")
async def api_start_campaign(req: StartCampaignRequest):
    try:
        message, campaign = await start_campaign(
            target_segment=req.target_segment,
            monthly_limit=req.monthly_limit,
            daily_limit=req.daily_limit
        )
        return {
            "message": message,
            "campaign_id": campaign.id,
            "status": campaign.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search_leads")
async def api_search_leads(campaign_id: str, query: str = ""):
    try:
        leads = await search_and_import_leads(campaign_id, query if query else None)
        return {
            "found": len(leads),
            "leads": [{"url": l.url, "email": l.email, "phone": l.phone, "company": l.company} for l in leads]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run_step")
async def api_run_step(campaign_id: str):
    try:
        result = await run_campaign_step(campaign_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/lead_response")
async def api_lead_response(campaign_id: str, req: LeadResponseRequest):
    try:
        result = await check_lead_response(campaign_id, req.lead_url, req.response_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/campaign/{campaign_id}")
async def api_get_campaign(campaign_id: str):
    status = get_campaign_status(campaign_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status

@app.get("/campaigns")
async def api_list_campaigns():
    return {"campaigns": list_campaigns()}

@app.post("/campaign/{campaign_id}/pause")
async def api_pause_campaign(campaign_id: str):
    campaign = load_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = "paused"
    save_campaign(campaign)
    return {"message": "Kampaň pozastavená", "status": "paused"}

@app.post("/campaign/{campaign_id}/resume")
async def api_resume_campaign(campaign_id: str):
    campaign = load_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = "running"
    save_campaign(campaign)
    return {"message": "Kampaň obnovená", "status": "running"}

@app.post("/call")
async def api_make_call(req: MakeCallRequest):
    try:
        result = make_call(req.phone, req.script)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sms")
async def api_send_sms(req: SendSmsRequest):
    try:
        result = send_sms(req.phone, req.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/daily_report")
async def api_daily_report():
    report = generate_daily_report()
    return {"report": report}

@app.post("/send_daily_report")
async def api_send_daily_report():
    result = send_daily_report()
    return result

@app.post("/run_daily_step")
async def api_run_daily_step():
    from campaign import run_daily_campaign_step
    result = await run_daily_campaign_step()
    return result

@app.get("/next_run")
async def api_next_run():
    from campaign import get_next_run_time
    return {"next_run": get_next_run_time()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7778)
