"""
Perplexity-like AI Search with Ollama
- Takes user query
- Generates smart sub-queries using Ollama
- Crawls multiple websites
- Summarizes content
- Provides final AI answer with sources
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import ollama
import json
from urllib.parse import quote_plus, urljoin
import re
from typing import Optional
from ddgs import DDGS
import ssl
import certifi
import feedparser
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────
OLLAMA_MODEL = "llama3.2:3b"       # Change to your model name
MAX_SEARCH_QUERIES = 5             # Sub-queries to generate (increased for comprehensive research)
MAX_RESULTS_PER_QUERY = 5          # Web results per sub-query (increased to get more sources)
MAX_CONTENT_LENGTH = 5000          # Chars to extract per page (increased for detailed articles)
REQUEST_TIMEOUT = 15               # Seconds per HTTP request (increased for slow sites)
USE_PLAYWRIGHT_FALLBACK = True     # Enable Playwright for JavaScript sites
# ──────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════
# STEP 1: Generate smart search queries using Ollama
# ══════════════════════════════════════════════════════════
def generate_search_queries(user_query: str) -> list[str]:
    """Ask Ollama to break down the query into targeted web searches."""
    print(f"\n🧠 Generating search queries for: '{user_query}'")

    prompt = f"""You are a search query optimizer. Given a user question, generate {MAX_SEARCH_QUERIES} specific, 
diverse web search queries that together will help answer the question comprehensively.

IMPORTANT RULES:
1. If the user asks about a specific website, use "site:" operator for that domain
   Example: "articles from example.com" → ["site:example.com latest", "site:example.com news"]

2. For comprehensive research queries (like writing an article), generate diverse queries that cover:
   - Historical facts and timeline
   - Technical specifications and capabilities
   - Official sources and documentation
   - Analysis and expert opinions
   - Recent news and updates
   
3. DO NOT restrict all queries to official government sites if they are timing out or blocking access
   - Mix official sources (with site:) and open web queries
   - Include Wikipedia, defense journals, news sites
   
4. For defense/military topics, also search: Wikipedia, defense news sites, aviation forums

User question: {user_query}

Return ONLY a JSON array of search query strings. No explanation, no markdown, just JSON.
Example: ["query 1", "query 2", "query 3", "query 4", "query 5"]"""

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response['message']['content'].strip()

    # Extract JSON array from response
    match = re.search(r'\[.*?\]', raw, re.DOTALL)
    if match:
        queries = json.loads(match.group())
        print(f"  ✅ Generated {len(queries)} queries: {queries}")
        return queries[:MAX_SEARCH_QUERIES]

    # Fallback: use original query
    print("  ⚠️  Could not parse queries, using original query")
    return [user_query]


# ══════════════════════════════════════════════════════════
# STEP 2: Search the web using DuckDuckGo
# ══════════════════════════════════════════════════════════
def search_web(queries: list[str]) -> list[dict]:
    """Use DuckDuckGo to find URLs for each query."""
    print(f"\n🔍 Searching the web...")
    all_results = []
    seen_urls = set()

    with DDGS() as ddgs:
        for query in queries:
            print(f"  🔎 Query: '{query}'")
            try:
                results = list(ddgs.text(query, max_results=MAX_RESULTS_PER_QUERY))
                for r in results:
                    url = r.get('href', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            'url': url,
                            'title': r.get('title', ''),
                            'snippet': r.get('body', ''),
                            'query': query
                        })
                        print(f"    📄 {r.get('title', 'Untitled')[:60]}...")
            except Exception as e:
                print(f"    ❌ Search error: {e}")

    print(f"\n  📊 Found {len(all_results)} unique URLs")
    return all_results


# ══════════════════════════════════════════════════════════
# STEP 2.5: Fetch RSS Feeds (Alternative to web crawling)
# ══════════════════════════════════════════════════════════
def fetch_rss_feed(feed_url: str, max_entries: int = 5) -> list[dict]:
    """Fetch and parse RSS/Atom feed from a URL."""
    print(f"\n📰 Fetching RSS feed from: {feed_url}")
    
    try:
        # Configure SSL context to be more lenient
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:  # Feed parsing error
            print(f"  ⚠️  Feed parsing error: {feed.get('bozo_exception', 'Unknown error')}")
            return []
        
        if not feed.entries:
            print(f"  ⚠️  No entries found in feed")
            return []
        
        articles = []
        for entry in feed.entries[:max_entries]:
            # Extract content (try different fields)
            content = (
                entry.get('content', [{}])[0].get('value', '') or
                entry.get('summary', '') or
                entry.get('description', '')
            )
            
            # Clean HTML from content
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                content = soup.get_text(separator=' ', strip=True)
            
            article = {
                'url': entry.get('link', ''),
                'title': entry.get('title', 'Untitled'),
                'content': content[:MAX_CONTENT_LENGTH],
                'published': entry.get('published', ''),
                'source': 'RSS Feed'
            }
            
            if article['content'] and len(article['content']) > 200:
                articles.append(article)
                print(f"  ✅ {article['title'][:60]}...")
        
        print(f"  📊 Fetched {len(articles)} articles from feed")
        return articles
        
    except Exception as e:
        print(f"  ❌ Error fetching RSS feed: {e}")
        return []


def get_common_rss_urls(domain: str) -> list[str]:
    """Generate common RSS feed URLs for a domain."""
    if not domain.startswith('http'):
        domain = f"https://{domain}"
    
    # Remove trailing slash
    domain = domain.rstrip('/')
    
    # Common RSS feed locations
    return [
        f"{domain}/feed",
        f"{domain}/rss",
        f"{domain}/feed/",
        f"{domain}/rss.xml",
        f"{domain}/atom.xml",
        f"{domain}/feeds/posts/default",
        f"{domain}/blog/feed",
        f"{domain}/blog/rss",
        f"{domain}/?feed=rss2",
    ]


def try_find_rss_feed(domain: str, max_articles: int = 5) -> list[dict]:
    """Try to find and fetch RSS feed from a domain."""
    print(f"\n🔍 Looking for RSS feed at {domain}...")
    
    possible_feeds = get_common_rss_urls(domain)
    
    for feed_url in possible_feeds:
        articles = fetch_rss_feed(feed_url, max_articles)
        if articles:
            print(f"  ✅ Found working feed: {feed_url}")
            return articles
    
    print(f"  ❌ No RSS feed found for {domain}")
    return []


# ══════════════════════════════════════════════════════════
# STEP 3: Crawl and extract content from each URL
# ══════════════════════════════════════════════════════════
async def fetch_page(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    """Fetch and clean text content from a URL."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT), allow_redirects=True) as resp:
            if resp.status != 200:
                print(f"    ⚠️  HTTP {resp.status}: {url[:70]}")
                return None
            
            # Check content type
            content_type = resp.headers.get('Content-Type', '')
            if 'text/html' not in content_type.lower():
                print(f"    ⚠️  Not HTML ({content_type}): {url[:70]}")
                return None
            
            html = await resp.text(errors='ignore')
            
            # Check if we got meaningful content
            if len(html) < 500:
                print(f"    ⚠️  Too short ({len(html)} chars): {url[:70]}")
                return None

            soup = BeautifulSoup(html, 'html.parser')

            # Remove noise
            for tag in soup(['script', 'style', 'nav', 'header', 'footer',
                             'aside', 'form', 'iframe', 'noscript', 'ads', 'button']):
                tag.decompose()

            # Try multiple strategies to find main content
            content = None
            
            # Strategy 1: Look for common article containers
            for selector in [
                {'name': 'article'},
                {'name': 'main'},
                {'name': 'div', 'class': re.compile(r'article|content|post|story|body|text', re.I)},
                {'name': 'div', 'id': re.compile(r'article|content|post|story|body|text', re.I)},
                {'name': 'div', 'role': 'main'},
            ]:
                content = soup.find(**selector)
                if content:
                    break
            
            # Strategy 2: Fallback to body
            if not content:
                content = soup.body
            
            if not content:
                print(f"    ⚠️  No content found: {url[:70]}")
                return None

            # Extract text
            text = content.get_text(separator=' ', strip=True)
            
            # Clean whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Check if we got meaningful text
            if len(text) < 200:
                print(f"    ⚠️  Content too short ({len(text)} chars): {url[:70]}")
                return None
            
            return text[:MAX_CONTENT_LENGTH]

    except asyncio.TimeoutError:
        print(f"    ⏱️  Timeout: {url[:70]}")
        return None
    except aiohttp.ClientError as e:
        print(f"    ❌ Client error: {url[:70]}")
        return None
    except Exception as e:
        print(f"    ❌ Error ({type(e).__name__}): {url[:70]}")
        return None


async def crawl_all_pages(search_results: list[dict]) -> list[dict]:
    """Crawl all pages concurrently."""
    print(f"\n🕷️  Crawling {len(search_results)} pages...")

    # Create SSL context
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context, limit=10)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_page(session, r['url']) for r in search_results]
        contents = await asyncio.gather(*tasks)

    enriched = []
    for result, content in zip(search_results, contents):
        if content and len(content) > 200:
            result['content'] = content
            enriched.append(result)
            print(f"  ✅ {result['url'][:70]}...")
        else:
            print(f"  ❌ Failed/empty: {result['url'][:70]}")

    print(f"\n  📊 Successfully crawled {len(enriched)} pages")
    return enriched


# ══════════════════════════════════════════════════════════
# STEP 3.5: Playwright fallback for JavaScript-heavy sites
# ══════════════════════════════════════════════════════════
async def fetch_with_playwright(url: str) -> Optional[str]:
    """Fetch page content using Playwright for JavaScript-rendered sites."""
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            try:
                # Navigate and wait for content
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Wait a bit for dynamic content
                await page.wait_for_timeout(2000)
                
                # Get the full HTML
                html = await page.content()
                
                await browser.close()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove noise
                for tag in soup(['script', 'style', 'nav', 'header', 'footer',
                                 'aside', 'form', 'iframe', 'noscript', 'ads', 'button']):
                    tag.decompose()
                
                # Try to find main content
                content = (
                    soup.find('article') or
                    soup.find('main') or
                    soup.find('div', class_=re.compile(r'article|content|post|story|body|text', re.I)) or
                    soup.body
                )
                
                if content:
                    text = content.get_text(separator=' ', strip=True)
                    text = re.sub(r'\s+', ' ', text).strip()
                    
                    if len(text) > 200:
                        return text[:MAX_CONTENT_LENGTH]
                
                return None
                
            except Exception as e:
                await browser.close()
                return None
                
    except ImportError:
        print(f"    ⚠️  Playwright not available, skipping")
        return None
    except Exception as e:
        return None


async def crawl_with_playwright(failed_urls: list[dict], max_urls: int = 3) -> list[dict]:
    """Retry failed URLs using Playwright for JavaScript rendering."""
    print(f"\n🎭 Attempting Playwright fallback for {min(len(failed_urls), max_urls)} pages...")
    print("   (This renders JavaScript - may take longer)")
    
    enriched = []
    urls_to_try = failed_urls[:max_urls]  # Limit to avoid long waits
    
    for i, result in enumerate(urls_to_try, 1):
        url = result['url']
        print(f"  [{i}/{len(urls_to_try)}] Playwright: {url[:60]}...")
        
        content = await fetch_with_playwright(url)
        
        if content and len(content) > 200:
            result['content'] = content
            result['source'] = 'Playwright'
            enriched.append(result)
            print(f"    ✅ Success via Playwright!")
        else:
            print(f"    ❌ Still failed")
    
    if enriched:
        print(f"\n  📊 Playwright fetched {len(enriched)} additional pages")
    else:
        print(f"\n  ❌ Playwright fallback did not help")
    
    return enriched


# ══════════════════════════════════════════════════════════
# STEP 4: Summarize each page with Ollama
# ══════════════════════════════════════════════════════════
def summarize_page(page: dict, original_query: str) -> str:
    """Use Ollama to extract relevant info from a page."""
    prompt = f"""Extract and summarize ONLY the information relevant to this question:
"{original_query}"

From this webpage content:
{page['content']}

Be concise (2-4 sentences). If the content is not relevant, say "Not relevant"."""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"Could not summarize: {e}"


def summarize_all_pages(pages: list[dict], original_query: str) -> list[dict]:
    """Summarize all crawled pages."""
    print(f"\n📝 Summarizing {len(pages)} pages with {OLLAMA_MODEL}...")

    for i, page in enumerate(pages, 1):
        print(f"  [{i}/{len(pages)}] Summarizing: {page['title'][:50]}...")
        page['summary'] = summarize_page(page, original_query)

    # Filter out non-relevant pages
    relevant = [p for p in pages if 'not relevant' not in p.get('summary', '').lower()]
    print(f"  ✅ {len(relevant)} relevant pages found")
    return relevant


# ══════════════════════════════════════════════════════════
# STEP 5: Generate final comprehensive answer
# ══════════════════════════════════════════════════════════
def generate_final_answer(query: str, pages: list[dict]) -> str:
    """Generate the final answer using all gathered context."""
    print(f"\n✨ Generating final answer with {OLLAMA_MODEL}...")

    # Build context from summaries
    context_parts = []
    for i, page in enumerate(pages[:8], 1):  # Max 8 sources
        context_parts.append(f"[Source {i}] {page['title']}\nURL: {page['url']}\n{page['summary']}")

    context = "\n\n".join(context_parts)

    prompt = f"""You are a helpful AI research assistant. Based on the following web search results, 
provide a comprehensive, accurate, and well-structured answer to the user's question.

USER QUESTION: {query}

SEARCH RESULTS:
{context}

Instructions:
- Provide a clear, detailed answer
- Cite sources using [Source N] notation  
- If sources conflict, mention it
- Structure with sections if needed
- Be factual and objective"""

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    return response['message']['content'].strip()


# ══════════════════════════════════════════════════════════
# STEP 6: Validate answer completeness
# ══════════════════════════════════════════════════════════
def validate_answer_coverage(query: str, answer: str) -> dict:
    """Check if the answer fully covers all aspects of the question."""
    print(f"\n🔍 Validating answer completeness...")
    
    prompt = f"""You are a critical evaluator. Analyze whether the provided answer fully addresses ALL aspects of the user's question.

USER QUESTION: {query}

GENERATED ANSWER:
{answer}

Task:
1. Identify if ANY topics/aspects from the question are missing or inadequately covered in the answer
2. If everything is well covered, respond with: {{"complete": true, "missing_topics": []}}
3. If something is missing, respond with: {{"complete": false, "missing_topics": ["topic1", "topic2"]}}

Return ONLY a JSON object. No explanation, just JSON.
Example 1: {{"complete": true, "missing_topics": []}}
Example 2: {{"complete": false, "missing_topics": ["modernization timeline", "specific performance metrics"]}}"""

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = response['message']['content'].strip()
    
    # Extract JSON from response
    import re
    match = re.search(r'\{.*?\}', raw, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if result.get('complete', True):
                print(f"  ✅ Answer is complete and covers all aspects!")
            else:
                missing = result.get('missing_topics', [])
                print(f"  ⚠️  Missing {len(missing)} topics: {', '.join(missing)}")
            return result
        except json.JSONDecodeError:
            print("  ⚠️  Could not parse validation response, assuming complete")
            return {"complete": True, "missing_topics": []}
    
    # Fallback: assume complete if can't parse
    print("  ⚠️  Could not validate, assuming answer is complete")
    return {"complete": True, "missing_topics": []}


# ══════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════
def run_search(query: str) -> dict:
    """Full Perplexity-like search pipeline."""
    print("=" * 60)
    print(f"🔬 RESEARCH QUERY: {query}")
    print("=" * 60)

    # Step 1: Generate smart queries
    queries = generate_search_queries(query)

    # Step 2: Search web
    search_results = search_web(queries)

    if not search_results:
        return {"error": "No search results found", "query": query}

    # Step 3: Crawl pages
    pages = asyncio.run(crawl_all_pages(search_results))

    if not pages:
        print("\n⚠️  WARNING: Could not fetch any page content!")
        print("💡 Possible reasons:")
        print("   - Website has anti-bot protection")
        print("   - Site requires JavaScript (not supported by simple crawler)")
        print("   - Connection/SSL issues")
        print("   - Paywall blocking content")
        
        # Try to extract domain and attempt RSS feed
        print("\n� Attempting RSS feed fallback...")
        domains_to_try = set()
        for result in search_results:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(result['url'])
                domain = parsed.netloc
                if domain:
                    domains_to_try.add(domain)
            except:
                pass
        
        # Try RSS for each unique domain
        rss_articles = []
        for domain in list(domains_to_try)[:3]:  # Try up to 3 domains
            print(f"\n   Trying RSS for {domain}...")
            articles = try_find_rss_feed(domain, max_articles=3)
            if articles:
                rss_articles.extend(articles)
        
        if rss_articles:
            print(f"\n✅ SUCCESS: Fetched {len(rss_articles)} articles via RSS feed!")
            pages = rss_articles
        else:
            print("\n❌ RSS fallback also failed.")
            print("\n�💡 Try asking a general question instead of targeting specific sites.")
            print("   Example: 'Latest defense technology news' instead of 'articles from defenceupdate.in'")
            return {
                "error": "Could not fetch any page content. Sites may have anti-bot protection or require JavaScript.",
                "query": query,
                "suggestion": "Try a general question instead of targeting specific websites.",
                "attempted_urls": [r['url'] for r in search_results]
            }
    
    if not pages:
        return {
            "error": "Could not fetch any page content. Sites may have anti-bot protection or require JavaScript.",
            "query": query,
            "suggestion": "Try a general question instead of targeting specific websites.",
            "attempted_urls": [r['url'] for r in search_results]
        }

    # Step 4: Summarize pages
    relevant_pages = summarize_all_pages(pages, query)

    if not relevant_pages:
        relevant_pages = pages  # Fallback to all pages

    # Step 5: Generate final answer
    final_answer = generate_final_answer(query, relevant_pages)

    # Step 6: Validate answer completeness
    validation = validate_answer_coverage(query, final_answer)
    
    # Step 7: If incomplete, search for missing topics
    if not validation.get('complete', True):
        missing_topics = validation.get('missing_topics', [])
        if missing_topics:
            print(f"\n🔄 Searching for missing topics: {', '.join(missing_topics)}")
            
            # Search for each missing topic
            additional_pages = []
            for topic in missing_topics[:3]:  # Limit to 3 missing topics
                follow_up_query = f"{query} {topic}"
                print(f"\n  🔎 Follow-up search: {topic}")
                
                # Generate specific search query for this topic
                follow_up_searches = generate_search_queries(follow_up_query)
                if follow_up_searches:
                    follow_up_results = search_web([follow_up_searches[0]])  # Just 1 query per topic
                    if follow_up_results:
                        follow_up_pages = asyncio.run(crawl_all_pages(follow_up_results[:3]))  # Max 3 URLs
                        if follow_up_pages:
                            summarized = summarize_all_pages(follow_up_pages, follow_up_query)
                            additional_pages.extend(summarized if summarized else follow_up_pages)
            
            if additional_pages:
                print(f"\n✅ Found {len(additional_pages)} additional sources for missing topics")
                # Combine with original pages
                all_pages = relevant_pages + additional_pages
                
                # Regenerate answer with complete information
                print(f"\n♻️  Regenerating answer with complete information...")
                final_answer = generate_final_answer(query, all_pages)
                
                # Update sources
                relevant_pages = all_pages
            else:
                print(f"\n⚠️  Could not find additional information for missing topics")

    # Build result
    result = {
        "query": query,
        "sub_queries": queries,
        "sources": [
            {
                "title": p['title'],
                "url": p['url'],
                "summary": p.get('summary', '')
            }
            for p in relevant_pages[:12]  # Increased to allow more sources
        ],
        "answer": final_answer,
        "validation": validation  # Include validation result
    }

    return result


def pretty_print_result(result: dict):
    """Display result nicely in terminal."""
    print("\n" + "=" * 60)
    print("📊 ANSWER")
    print("=" * 60)
    print(result.get('answer', 'No answer generated'))

    print("\n" + "=" * 60)
    print("📚 SOURCES")
    print("=" * 60)
    for i, src in enumerate(result.get('sources', []), 1):
        print(f"\n[{i}] {src['title']}")
        print(f"    🔗 {src['url']}")
        print(f"    📝 {src['summary'][:150]}...")


# ══════════════════════════════════════════════════════════
# CLI Entry Point
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("\n🔍 Enter your question: ").strip()
        if not query:
            query = "What are the latest AI developments in 2025?"

    result = run_search(query)
    pretty_print_result(result)

    # Save to JSON
    with open("result.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\n💾 Full result saved to result.json")
