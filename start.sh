#!/bin/bash

# Perplexity Clone - Quick Start Script
# This script verifies everything is working and provides run instructions

echo "======================================================================"
echo "🔭 Ollama Perplexity Clone - System Check"
echo "======================================================================"

echo ""
echo "Checking Ollama..."
if command -v ollama &> /dev/null; then
    echo "✅ Ollama is installed"
    echo ""
    echo "Available models:"
    ollama list
else
    echo "❌ Ollama is not installed"
    echo "   Install from: https://ollama.com"
    exit 1
fi

echo ""
echo "Checking Python environment..."
if [ -d ".venv" ]; then
    echo "✅ Virtual environment found"
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  No virtual environment found"
    echo "   You may need to create one:"
    echo "   python3 -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements.txt"
fi

echo ""
echo "Running quick test..."
.venv/bin/python quick_test.py

echo ""
echo "======================================================================"
echo "🚀 HOW TO RUN THE PROJECT"
echo "======================================================================"
echo ""
echo "Option 1: Web Interface (Recommended)"
echo "  .venv/bin/uvicorn server:app --reload --port 8000"
echo "  Then open: http://localhost:8000"
echo ""
echo "Option 2: Command Line"
echo "  .venv/bin/python app.py 'Your question here'"
echo ""
echo "======================================================================"
