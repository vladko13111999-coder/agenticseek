#!/bin/bash

# Brand Twin AI - Startup Script for RunPod
# Run this after container reset

set -e

echo "=========================================="
echo "Brand Twin AI - Starting Services"
echo "=========================================="

# Change to agenticseek directory
cd ~/agenticseek

# 1. Install Chromium and chromedriver
echo "[1/6] Installing Chromium and chromedriver..."
if ! command -v chromium-browser &> /dev/null; then
    apt-get update && apt-get install -y chromium-browser chromium-chromedriver
else
    echo "  Chromium already installed"
fi

# 2. Download Image Turbo model (if not exists)
echo "[2/6] Checking Image model..."
if ! ollama list | grep -q "image-turbo"; then
    echo "  Pulling stable-diffusion as fallback image model..."
    ollama pull stable-diffusion
    ollama cp stable-diffusion image-turbo || echo "  Could not rename, using stable-diffusion"
else
    echo "  Image model already installed"
fi

# 3. Start Ollama daemon
echo "[3/6] Starting Ollama daemon..."
export OLLAMA_HOST=0.0.0.0:11434
pkill -f "ollama serve" || true
ollama serve &
sleep 5

# 4. Verify Ollama and models
echo "[4/6] Verifying Ollama and models..."
ollama list

# 5. Install Python dependencies
echo "[5/6] Installing Python dependencies..."
pip3 install -r requirements.txt --quiet 2>/dev/null || pip3 install -r requirements.txt

# 6. Start API server
echo "[6/6] Starting Brand Twin API..."
pkill -f "python.*api.py" || true
nohup python3 api.py > api.log 2>&1 &
sleep 5

# Verify API is running
echo ""
echo "=========================================="
echo "Services Status:"
echo "=========================================="
echo ""
echo "Ollama:"
ps aux | grep "ollama serve" | grep -v grep || echo "  NOT RUNNING"
echo ""
echo "API Server:"
ps aux | grep "python.*api.py" | grep -v grep || echo "  NOT RUNNING"
echo ""
echo "API Health Check:"
curl -s http://localhost:7777/health || echo "  FAILED"
echo ""
echo "=========================================="
echo "API URL: https://37gt7a0hmcbdqm-7777.proxy.runpod.net"
echo "=========================================="
