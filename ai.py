"""
AI Module - Ollama Integration
Handles all AI/LLM operations
"""

import ollama
import json
import re


OLLAMA_MODEL = "llama3.2:3b"


def generate_search_queries(user_query: str, num_queries: int = 5) -> list[str]:
    """Generate targeted search queries using AI."""
    print(f"\n🧠 Generating search queries for: '{user_query}'")
    
    prompt = f"""Generate {num_queries} diverse web search queries to answer this question comprehensively.

Rules:
- Mix Wikipedia, official docs, tutorials, and news sites
- Use simple, direct search terms (avoid site: unless user specifically asks)
- Cover different aspects of the question
- Prefer accessible, crawlable sites

Question: {user_query}

Return ONLY a JSON array: ["query1", "query2", "query3", "query4", "query5"]"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw = response['message']['content'].strip()
        
        # Extract JSON
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            queries = json.loads(match.group())
            print(f"  ✅ Generated {len(queries)} queries")
            return queries[:num_queries]
    except Exception as e:
        print(f"  ⚠️  Error generating queries: {e}")
    
    # Fallback
    return [user_query]


def summarize_page(content: str, query: str, title: str) -> str:
    """Summarize page content relevant to the query."""
    prompt = f"""Extract and summarize ONLY information relevant to: "{query}"

From this webpage: {title}

Content:
{content[:3000]}

Provide a concise summary (max 300 words) of relevant information only.
If nothing is relevant, say "No relevant information found."
"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"Error summarizing: {str(e)}"


def generate_answer(query: str, summaries: list[dict]) -> str:
    """Generate comprehensive answer from summaries."""
    print(f"\n✨ Generating final answer with {OLLAMA_MODEL}...")
    
    # Build context
    context_parts = []
    for i, page in enumerate(summaries[:12], 1):
        context_parts.append(f"[Source {i}] {page['title']}\nURL: {page['url']}\n{page['summary']}")
    
    context = "\n\n".join(context_parts)
    
    prompt = f"""You are a helpful research assistant. Based on these web sources, provide a comprehensive answer.

USER QUESTION: {query}

SOURCES:
{context}

Instructions:
- Provide clear, detailed answer
- Cite sources using [Source N]
- Structure with sections if needed
- Note conflicts if any
- Be factual and objective
"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"Error generating answer: {str(e)}"


def validate_answer(query: str, answer: str) -> dict:
    """Check if answer covers all aspects of the question."""
    print(f"\n🔍 Validating answer completeness...")
    
    prompt = f"""Analyze if this answer fully addresses ALL aspects of the question.

QUESTION: {query}

ANSWER:
{answer}

Return JSON only:
{{"complete": true/false, "missing_topics": ["topic1", "topic2"]}}

If complete, return empty list. If incomplete, list missing topics.
"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw = response['message']['content'].strip()
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        
        if match:
            result = json.loads(match.group())
            if result.get('complete', True):
                print(f"  ✅ Answer is complete!")
            else:
                missing = result.get('missing_topics', [])
                print(f"  ⚠️  Missing {len(missing)} topics: {', '.join(missing)}")
            return result
    except Exception as e:
        print(f"  ⚠️  Validation error: {e}")
    
    return {"complete": True, "missing_topics": []}


def extract_json(text: str) -> dict:
    """Safely extract JSON from model response."""
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == -1:
            return None
        return json.loads(text[start:end])
    except Exception:
        return None


def validate_schema(result: dict) -> dict:
    """Ensure returned JSON has required fields."""
    default = {
        "accuracy_score": 0,
        "accurate_claims": [],
        "unsupported_claims": [],
        "contradicted_claims": [],
        "issues": [],
        "verdict": "unknown"
    }

    if not isinstance(result, dict):
        return default

    for k in default:
        result.setdefault(k, default[k])

    return result


def fact_check_answer(answer: str, sources: list) -> dict:
    """Verify factual accuracy of answer against sources using LLM."""
    
    print("\n🔬 Fact-checking answer against sources...")

    # Limit number of sources to avoid context overflow
    MAX_SOURCES = 6
    sources = sources[:MAX_SOURCES]

    source_text = "\n\n---\n\n".join(
        f"SOURCE {i+1} ({s.get('url','Unknown')}):\n{s.get('summary','')}"
        for i, s in enumerate(sources)
    )

    prompt = f"""You are a strict AI fact-checker.

Your task is to verify the accuracy of the answer using ONLY the provided sources.

Classify claims into:
- ACCURATE: clearly supported by sources
- UNSUPPORTED: not present in sources
- CONTRADICTED: conflicts with sources
- EXAGGERATED: overstates what sources say

ANSWER:
{answer}

SOURCES:
{source_text}

Return ONLY valid JSON.

{{
  "accuracy_score": 0-100,
  "accurate_claims": [],
  "unsupported_claims": [],
  "contradicted_claims": [],
  "issues": [],
  "verdict": "accurate | mostly_accurate | partially_accurate | inaccurate"
}}
"""

    MAX_RETRIES = 2

    for attempt in range(MAX_RETRIES):

        try:
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0,  # deterministic for fact-checking
                    "num_ctx": 4096
                }
            )

            raw = response["message"]["content"].strip()

            result = extract_json(raw)

            if result:
                result = validate_schema(result)

                score = result.get("accuracy_score", 0)
                verdict = result.get("verdict", "unknown")

                if verdict == "accurate":
                    print(f"  ✅ Fact-check PASSED (Score: {score}/100)")

                elif verdict == "mostly_accurate":
                    print(f"  ✓  Fact-check: Mostly Accurate (Score: {score}/100)")
                    issues = result.get("issues", [])
                    if issues:
                        print(f"     Minor issues: {', '.join(issues[:2])}")

                else:
                    print(f"  ⚠️ Fact-check WARNING (Score: {score}/100)")
                    unsupported = result.get("unsupported_claims", [])
                    contradicted = result.get("contradicted_claims", [])

                    if unsupported:
                        print(f"     Unsupported claims: {len(unsupported)}")

                    if contradicted:
                        print(f"     Contradicted claims: {len(contradicted)}")

                return result

        except Exception as e:
            print(f"  ⚠️ Attempt {attempt+1} failed: {e}")

    # fallback if model fails
    return {
        "accuracy_score": 0,
        "accurate_claims": [],
        "unsupported_claims": [],
        "contradicted_claims": [],
        "issues": ["fact_check_failed"],
        "verdict": "unknown"
    }
