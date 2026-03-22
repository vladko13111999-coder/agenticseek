#!/bin/bash

# Brand Twin AI - Startup Script for RunPod
# Run this after container reset

set -e

echo "=========================================="
echo "Brand Twin AI - Starting Services"
echo "=========================================="

# Change to agenticseek directory
cd ~/agenticseek

# 1. Install/Update system dependencies if needed
echo "[1/5] Checking system dependencies..."
if ! command -v chromium-browser &> /dev/null; then
    echo "Installing chromium-browser..."
    apt-get update && apt-get install -y chromium-browser chromium-chromedriver
fi

# 2. Start Ollama daemon
echo "[2/5] Starting Ollama daemon..."
export OLLAMA_HOST=0.0.0.0:11434
pkill -f "ollama serve" || true
ollama serve &
sleep 3

# 3. Verify Ollama is running
echo "[3/5] Verifying Ollama..."
ollama list

# 4. Install Python dependencies
echo "[4/5] Installing Python dependencies..."
pip3 install -r requirements.txt --quiet

# 5. Start API server
echo "[5/5] Starting Brand Twin API..."
pkill -f "python.*api.py" || true
nohup python3 api.py > api.log 2>&1 &
sleep 3

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
