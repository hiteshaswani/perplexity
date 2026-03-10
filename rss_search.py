"""
RSS Feed Reader for Perplexity Clone
Fetch articles from RSS feeds instead of web crawling
Usage: python rss_search.py "domain.com" --max-articles 5
"""

import sys
import json
from app import (
    try_find_rss_feed, 
    summarize_page, 
    generate_final_answer,
    OLLAMA_MODEL,
    pretty_print_result
)

def rss_search(domain: str, query: str = None, max_articles: int = 5) -> dict:
    """Search using RSS feed instead of web crawling."""
    
    print("=" * 60)
    print(f"📰 RSS FEED SEARCH: {domain}")
    if query:
        print(f"🔬 CONTEXT QUERY: {query}")
    print("=" * 60)
    
    # Try to find and fetch RSS feed
    articles = try_find_rss_feed(domain, max_articles)
    
    if not articles:
        return {
            "error": "No RSS feed found or no articles available",
            "domain": domain,
            "suggestion": "Try using the regular search with a general question instead"
        }
    
    # If user provided a query, summarize articles in that context
    if query:
        print(f"\n📝 Summarizing {len(articles)} articles with {OLLAMA_MODEL}...")
        for i, article in enumerate(articles, 1):
            print(f"  [{i}/{len(articles)}] Summarizing: {article['title'][:50]}...")
            article['summary'] = summarize_page(article, query)
        
        # Filter relevant articles
        relevant = [a for a in articles if 'not relevant' not in a.get('summary', '').lower()]
        print(f"  ✅ {len(relevant)} relevant articles found")
        
        if not relevant:
            relevant = articles  # Use all if none specifically relevant
        
        # Generate final answer
        final_answer = generate_final_answer(query, relevant)
        
        result = {
            "domain": domain,
            "query": query,
            "articles_fetched": len(articles),
            "sources": [
                {
                    "title": a['title'],
                    "url": a['url'],
                    "published": a.get('published', ''),
                    "summary": a.get('summary', a['content'][:200])
                }
                for a in relevant
            ],
            "answer": final_answer
        }
    else:
        # No query - just list articles
        result = {
            "domain": domain,
            "articles_fetched": len(articles),
            "articles": [
                {
                    "title": a['title'],
                    "url": a['url'],
                    "published": a.get('published', ''),
                    "preview": a['content'][:200] + "..."
                }
                for a in articles
            ]
        }
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch articles from RSS feeds')
    parser.add_argument('domain', help='Domain to fetch RSS from (e.g., defenceupdate.in)')
    parser.add_argument('-q', '--query', help='Context query for summarization', default=None)
    parser.add_argument('-n', '--max-articles', type=int, default=5, help='Maximum articles to fetch')
    
    args = parser.parse_args()
    
    result = rss_search(args.domain, args.query, args.max_articles)
    
    if 'error' in result:
        print("\n" + "=" * 60)
        print("❌ ERROR")
        print("=" * 60)
        print(result['error'])
        print("\n💡 Suggestion:", result.get('suggestion', ''))
    elif 'answer' in result:
        pretty_print_result(result)
    else:
        # Just listing articles
        print("\n" + "=" * 60)
        print("📰 ARTICLES FOUND")
        print("=" * 60)
        for i, article in enumerate(result['articles'], 1):
            print(f"\n[{i}] {article['title']}")
            print(f"    🔗 {article['url']}")
            if article.get('published'):
                print(f"    📅 {article['published']}")
            print(f"    📝 {article['preview']}")
    
    # Save to JSON
    with open("rss_result.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\n💾 Full result saved to rss_result.json")
