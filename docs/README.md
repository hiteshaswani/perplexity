# 🔭 OllamaSearch — Local Perplexity Clone

A Perplexity-like AI search engine that runs **entirely on your machine** using Ollama + DuckDuckGo.

## How It Works

```
User Query
    ↓
[Ollama] Generate 3 smart sub-queries
    ↓
[DuckDuckGo] Search web → get URLs
    ↓
[aiohttp] Crawl pages concurrently → extract text
    ↓
[Ollama] Summarize each page for relevance
    ↓
[Ollama] Generate final comprehensive answer with citations
    ↓
Display answer + sources
```

## Setup

### 1. Install Ollama
```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows: download from https://ollama.com
```

### 2. Pull a model
```bash
ollama pull llama3.2          # Fast, good quality (~2GB)
# or
ollama pull mistral           # Alternative
ollama pull qwen2.5           # Also great
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure model
Edit `app.py` line 18:
```python
OLLAMA_MODEL = "llama3.2"    # ← Change to your model
```

---

## Usage

### Option A: CLI (Terminal)
```bash
# Single query
python app.py "What is quantum computing?"

# Interactive mode
python app.py
```

### Option B: Web UI (Recommended)
```bash
uvicorn server:app --reload --port 8000
# Open http://localhost:8000
```

The web UI auto-detects your Ollama models and shows
a live step-by-step pipeline as it searches.

---

## Configuration (`app.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.2` | Your Ollama model name |
| `MAX_SEARCH_QUERIES` | `3` | Sub-queries to generate |
| `MAX_RESULTS_PER_QUERY` | `3` | URLs per sub-query |
| `MAX_CONTENT_LENGTH` | `3000` | Chars to extract per page |
| `REQUEST_TIMEOUT` | `10` | HTTP timeout per page |

---

## Project Structure

```
ollama-perplexity/
├── app.py          # Core pipeline (queries → crawl → summarize → answer)
├── server.py       # FastAPI web server
├── index.html      # Web UI frontend
├── requirements.txt
└── README.md
```

---

## Troubleshooting

**"Connection refused" error**
- Make sure Ollama is running: `ollama serve`

**Slow responses**
- Use a smaller/faster model: `ollama pull phi3`
- Reduce `MAX_RESULTS_PER_QUERY` to 2

**DuckDuckGo rate limited**
- Add `time.sleep(1)` between searches in `search_web()`
