"""
HTTP Web Crawler Module
Handles fetching and parsing web pages
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import ssl
import certifi

# Configuration
REQUEST_TIMEOUT = 10  # Reduced from 15 to 10 seconds
MAX_CONTENT_LENGTH = 5000
MAX_CONCURRENT_REQUESTS = 20  # NEW: Limit concurrent requests
CONNECTOR_LIMIT = 100  # NEW: Connection pool size


async def fetch_page(url: str) -> dict:
    """Fetch a single page via HTTP."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, ssl=ssl_context) as resp:
                if resp.status != 200:
                    return {'url': url, 'content': None, 'error': f'HTTP {resp.status}'}
                
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove noise
                for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
                    tag.decompose()
                
                # Try multiple strategies to extract content
                content = None
                
                # Strategy 1: article tag
                article = soup.find('article')
                if article:
                    content = article.get_text(separator=' ', strip=True)
                
                # Strategy 2: main tag
                if not content or len(content) < 200:
                    main = soup.find('main')
                    if main:
                        content = main.get_text(separator=' ', strip=True)
                
                # Strategy 3: div with common content classes
                if not content or len(content) < 200:
                    for class_name in ['content', 'article', 'post', 'entry', 'main-content']:
                        div = soup.find('div', class_=lambda x: x and class_name in x.lower())
                        if div:
                            content = div.get_text(separator=' ', strip=True)
                            if len(content) > 200:
                                break
                
                # Strategy 4: all paragraphs
                if not content or len(content) < 200:
                    paragraphs = soup.find_all('p')
                    content = ' '.join([p.get_text(strip=True) for p in paragraphs])
                
                # Limit content length
                if content:
                    content = content[:MAX_CONTENT_LENGTH]
                
                title = soup.title.string if soup.title else 'Untitled'
                return {'url': url, 'content': content, 'title': title}
                
    except asyncio.TimeoutError:
        return {'url': url, 'content': None, 'error': 'Timeout'}
    except Exception as e:
        return {'url': url, 'content': None, 'error': str(e)}


async def crawl_pages(urls: list[str]) -> list[dict]:
    """Crawl multiple pages concurrently with optimized connection pooling."""
    print(f"\n🕷️  Crawling {len(urls)} pages in parallel...")
    
    # Create a single session with connection pooling
    connector = aiohttp.TCPConnector(
        limit=CONNECTOR_LIMIT,
        limit_per_host=10,
        ttl_dns_cache=300,
        ssl=False  # We handle SSL in fetch_page
    )
    
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT, connect=5)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        
        async def fetch_with_semaphore(url):
            async with semaphore:
                return await fetch_page_with_session(session, url)
        
        # Fetch all URLs concurrently (but limited by semaphore)
        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    successful = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            url = urls[i]
            print(f"  ❌ Exception: {url[:60]}...")
            continue
            
        url = result['url']
        content = result.get('content')
        error = result.get('error')
        
        if error:
            print(f"  ❌ {error}: {url[:60]}...")
        elif not content or len(content) < 200:
            print(f"  ⚠️  Content too short: {url[:60]}...")
        else:
            print(f"  ✅ {url[:60]}...")
            successful.append(result)
    
    print(f"\n  📊 Successfully crawled {len(successful)} pages")
    return successful


async def fetch_page_with_session(session: aiohttp.ClientSession, url: str) -> dict:
    """Fetch a single page using an existing session."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        async with session.get(url, headers=headers, ssl=ssl_context) as resp:
            if resp.status != 200:
                return {'url': url, 'content': None, 'error': f'HTTP {resp.status}'}
            
            html = await resp.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove noise
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
                tag.decompose()
            
            # Try multiple strategies to extract content
            content = None
            
            # Strategy 1: article tag
            article = soup.find('article')
            if article:
                content = article.get_text(separator=' ', strip=True)
            
            # Strategy 2: main tag
            if not content or len(content) < 200:
                main = soup.find('main')
                if main:
                    content = main.get_text(separator=' ', strip=True)
            
            # Strategy 3: div with common content classes
            if not content or len(content) < 200:
                for class_name in ['content', 'article', 'post', 'entry', 'main-content']:
                    div = soup.find('div', class_=lambda x: x and class_name in x.lower())
                    if div:
                        content = div.get_text(separator=' ', strip=True)
                        if len(content) > 200:
                            break
            
            # Strategy 4: all paragraphs
            if not content or len(content) < 200:
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text(strip=True) for p in paragraphs])
            
            # Limit content length
            if content:
                content = content[:MAX_CONTENT_LENGTH]
            
            return {'url': url, 'content': content, 'title': soup.title.string if soup.title else 'Untitled'}
            
    except asyncio.TimeoutError:
        return {'url': url, 'content': None, 'error': 'Timeout'}
    except Exception as e:
        return {'url': url, 'content': None, 'error': str(e)}
