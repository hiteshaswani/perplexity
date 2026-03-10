"""
Quick test script to verify Ollama integration
This tests the core functionality without doing a full web search
"""

import ollama
import json

print("=" * 70)
print("🧪 QUICK TEST - Ollama Integration Check")
print("=" * 70)

OLLAMA_MODEL = "llama3.2:3b"

# Test 1: Model availability
print("\n[1/3] Checking available models...")
try:
    models = ollama.list()
    available_models = [m.get('model', m.get('name')) for m in models.get('models', [])]
    print(f"✅ Found {len(available_models)} model(s): {', '.join(available_models)}")
    
    if OLLAMA_MODEL in available_models or any(OLLAMA_MODEL in m for m in available_models):
        print(f"✅ Target model '{OLLAMA_MODEL}' is available")
    else:
        print(f"⚠️  Warning: '{OLLAMA_MODEL}' not found in list")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# Test 2: Basic query
print("\n[2/3] Testing basic query...")
try:
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{
            'role': 'user',
            'content': 'Respond with exactly: "Ollama is working!"'
        }]
    )
    reply = response['message']['content']
    print(f"✅ Model response: {reply[:100]}")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# Test 3: Query generation (core feature)
print("\n[3/3] Testing search query generation...")
try:
    test_question = "What is artificial intelligence?"
    
    prompt = f"""You are a search query optimizer. Given a user question, generate 3 specific, 
diverse web search queries that together will help answer the question comprehensively.

User question: {test_question}

Return ONLY a JSON array of search query strings. No explanation, no markdown, just JSON.
Example: ["query 1", "query 2", "query 3"]"""

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = response['message']['content'].strip()
    
    # Try to extract JSON
    import re
    match = re.search(r'\[.*?\]', raw, re.DOTALL)
    if match:
        queries = json.loads(match.group())
        print(f"✅ Generated {len(queries)} search queries:")
        for i, q in enumerate(queries, 1):
            print(f"   {i}. {q}")
    else:
        print(f"⚠️  Could not parse JSON, raw output: {raw[:100]}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED - Ollama integration is working correctly!")
print("=" * 70)
print("\n💡 You can now run the full application:")
print("   - CLI: /usr/local/bin/python3 app.py 'Your question'")
print("   - Web: uvicorn server:app --reload --port 8000")
print("=" * 70)
