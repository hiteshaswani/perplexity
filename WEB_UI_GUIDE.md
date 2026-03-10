# Web UI Guide

## 🚀 Quick Start

### 1. Start the Server
```bash
cd /Users/hiteshaswani/Developer/Perplexity
.venv/bin/python -m uvicorn server:app --reload --port 8000
```

### 2. Open Browser
Navigate to: **http://localhost:8000**

---

## 🎨 New Interface Features

### Clean Perplexity-Style UI
- **Dark theme** optimized for readability
- **Responsive design** works on all devices
- **Real-time status** shows research progress
- **Beautiful results** with proper formatting

### Three-Phase Pipeline Display

#### 1. Answer Section
- Comprehensive answer with markdown formatting
- Validation badge showing completeness
- Clear, structured content

#### 2. Fact-Check Card
- **Accuracy score** (0-100) with color coding
  - ✅ Green (90-100): Accurate
  - ⚠️ Yellow (70-89): Mostly accurate
  - ❌ Red (0-69): Needs verification
- **Verdict badges**: accurate | mostly_accurate | partially_accurate | inaccurate
- **Issue reporting**: Shows unsupported/contradicted claims

#### 3. Sources Grid
- Clickable source cards
- URL display with domain highlighting
- Summary preview (150 chars)
- Numbered references matching answer

---

## 📱 UI Components

### Search Box
```
🔎 Ask anything... e.g., 'What is quantum computing?'
```
- Auto-focus on page load
- Enter key to search
- Clear placeholder text

### Status Messages
- 🔄 **Loading**: "Researching your question..."
- ✅ **Success**: "Research complete!"
- ❌ **Error**: Shows error details

### Answer Card
```
📊 ANSWER
─────────────────────
[Formatted answer with markdown]

✅ Complete Coverage
OR
⚠️ Missing: [topics]
```

### Fact Check Card
```
🔬 FACT CHECK
─────────────────────
✅ 95/100

⚠️ Unsupported claims: [list]
❌ Contradicted: [list]
📝 Issues: [list]
```

### Source Cards
```
[1] Source Title
    example.com
    Summary preview text...
```
- Hover effect with lift animation
- Click to open in new tab
- Color-coded borders

---

## 🎯 Example Queries

### Simple Factual
```
What is the capital of France?
```
**Expected**: Quick answer with 100% accuracy

### Complex Research
```
Write an article on Su-30 MKI history with India
```
**Expected**: 
- Multiple sources (8-12)
- Complete validation
- High accuracy score (90-95%)

### Technical Deep-Dive
```
Explain quantum computing applications and challenges
```
**Expected**:
- Comprehensive coverage
- Multiple technical sources
- Validation with follow-up searches

---

## 🔧 API Endpoints

### Main Interface
- **URL**: `http://localhost:8000`
- **Method**: GET
- **Returns**: HTML page (search.html)

### Old Interface (Legacy)
- **URL**: `http://localhost:8000/old`
- **Method**: GET
- **Returns**: Original index.html

### Search API
- **URL**: `http://localhost:8000/search`
- **Method**: POST
- **Body**: 
```json
{
  "query": "Your question here"
}
```
- **Response**:
```json
{
  "query": "...",
  "sub_queries": [...],
  "sources": [...],
  "answer": "...",
  "validation": {
    "complete": true,
    "missing_topics": []
  },
  "fact_check": {
    "accuracy_score": 95,
    "verdict": "accurate",
    "unsupported_claims": [],
    "contradicted_claims": [],
    "issues": []
  }
}
```

### Models API
- **URL**: `http://localhost:8000/models`
- **Method**: GET
- **Returns**: List of available Ollama models

### Health Check
- **URL**: `http://localhost:8000/health`
- **Method**: GET
- **Returns**: Server status

---

## 🎨 Color Scheme

### Variables
```css
--bg-primary: #0f0f0f     /* Main background */
--bg-secondary: #1a1a1a   /* Cards background */
--bg-tertiary: #252525    /* Hover states */
--accent: #20b8cd         /* Primary accent (cyan) */
--text-primary: #efefef   /* Main text */
--text-secondary: #b4b4b4 /* Muted text */
--success: #4ade80        /* Green for success */
--warning: #fbbf24        /* Yellow for warnings */
--error: #f87171          /* Red for errors */
```

---

## 🖥️ Browser Compatibility

### Fully Supported
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

### Features Used
- CSS Grid & Flexbox
- CSS Custom Properties (Variables)
- Fetch API
- ES6+ JavaScript
- Async/Await

---

## 📊 Performance

### Average Response Times
- **Simple queries**: 10-15 seconds
- **Complex queries**: 25-45 seconds
- **UI render time**: <100ms

### Resource Usage
- **Memory**: ~100MB (frontend)
- **Network**: ~50-200KB per request
- **CPU**: Minimal (async operations)

---

## 🐛 Troubleshooting

### UI Not Loading
```bash
# Check if server is running
curl http://localhost:8000

# Restart server
pkill -f uvicorn
.venv/bin/python -m uvicorn server:app --reload --port 8000
```

### Search Not Working
1. Check browser console (F12)
2. Verify API endpoint: `http://localhost:8000/search`
3. Check CORS settings in server.py
4. Ensure Ollama is running: `ollama list`

### Styling Issues
- Clear browser cache (Ctrl+Shift+R)
- Check if search.html exists
- Verify CSS is not blocked

### Slow Responses
- Check Ollama model is loaded: `ollama ps`
- Reduce MAX_SEARCH_QUERIES in app_simple.py
- Check network connectivity

---

## 🚀 Deployment

### Local Development
```bash
uvicorn server:app --reload --port 8000
```

### Production
```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker (Optional)
```dockerfile
FROM python:3.13
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📝 Customization

### Change Theme Colors
Edit CSS variables in `search.html`:
```css
:root {
    --accent: #20b8cd;  /* Change to your color */
}
```

### Modify Layout
- Search box: `.search-section`
- Results: `.results`
- Cards: `.answer-card`, `.source-card`

### Add Features
- Edit JavaScript section in `search.html`
- API calls in `search()` function
- Display logic in `displayResults()`

---

## 🔗 Links

- **Frontend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Swagger UI**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## ✨ Features Summary

✅ **Clean UI** - Perplexity-style dark theme
✅ **Real-time Status** - Loading states with spinner
✅ **Fact-Checking** - Accuracy scores with color coding
✅ **Validation Display** - Coverage indicators
✅ **Source Cards** - Clickable with summaries
✅ **Responsive** - Works on mobile/tablet/desktop
✅ **Error Handling** - User-friendly error messages
✅ **Fast Rendering** - Optimized DOM operations
✅ **Keyboard Support** - Enter to search
✅ **Auto-focus** - Ready to type immediately
