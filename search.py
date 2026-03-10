"""
Web Search Module
Handles DuckDuckGo search queries
"""

from ddgs import DDGS


def search_web(queries: list[str], results_per_query: int = 5) -> list[dict]:
    """Search DuckDuckGo for multiple queries."""
    print(f"\n🔍 Searching the web...")
    
    all_results = []
    seen_urls = set()
    
    for query in queries:
        print(f"  🔎 Query: '{query}'")
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=results_per_query))
                
                for result in results:
                    url = result.get('href', result.get('url', ''))
                    
                    # Skip duplicates
                    if url in seen_urls:
                        continue
                    
                    seen_urls.add(url)
                    all_results.append({
                        'url': url,
                        'title': result.get('title', ''),
                        'snippet': result.get('body', '')
                    })
                    
                    print(f"    📄 {result.get('title', 'No title')[:60]}...")
                    
        except Exception as e:
            print(f"    ❌ Search error: {str(e)}")
    
    print(f"\n  📊 Found {len(all_results)} unique URLs")
    return all_results
