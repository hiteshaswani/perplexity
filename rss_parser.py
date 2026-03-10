"""
RSS Feed Parser Module
Handles RSS/Atom feed fetching and parsing
"""

import feedparser
import ssl


def fetch_rss_feed(feed_url: str, max_articles: int = 5) -> list[dict]:
    """Fetch and parse RSS/Atom feed."""
    try:
        # Disable SSL verification for feeds
        ssl._create_default_https_context = ssl._create_unverified_context
        
        feed = feedparser.parse(feed_url)
        
        if not feed.entries:
            return []
        
        articles = []
        for entry in feed.entries[:max_articles]:
            title = entry.get('title', 'No title')
            link = entry.get('link', '')
            summary = entry.get('summary', entry.get('description', ''))
            
            # Clean HTML from summary
            from bs4 import BeautifulSoup
            if summary:
                soup = BeautifulSoup(summary, 'html.parser')
                summary = soup.get_text(separator=' ', strip=True)[:3000]
            
            articles.append({
                'title': title,
                'url': link,
                'content': summary,
                'source': 'RSS'
            })
        
        return articles
        
    except Exception as e:
        return []


def try_find_rss_feed(domain: str, max_articles: int = 5) -> list[dict]:
    """Try to find RSS feed for a domain by testing common locations."""
    # Common RSS feed URLs
    common_feeds = [
        f"https://{domain}/feed",
        f"https://{domain}/rss",
        f"https://{domain}/atom.xml",
        f"https://{domain}/rss.xml",
        f"https://{domain}/feed.xml",
        f"https://{domain}/feeds/posts/default",
        f"https://{domain}/blog/feed",
        f"https://{domain}/news/rss",
        f"https://{domain}/index.xml",
    ]
    
    for feed_url in common_feeds:
        articles = fetch_rss_feed(feed_url, max_articles)
        if articles:
            return articles
    
    return []


def fetch_rss_fallback(failed_urls: list[str], max_articles: int = 3) -> list[dict]:
    """Try RSS feeds for domains that failed HTTP crawling."""
    print("\n📰 Attempting RSS feed fallback...")
    
    # Extract unique domains
    from urllib.parse import urlparse
    domains = set()
    for url in failed_urls:
        try:
            parsed = urlparse(url)
            if parsed.netloc:
                domains.add(parsed.netloc)
        except:
            pass
    
    # Try RSS for each domain
    all_articles = []
    for domain in list(domains)[:3]:  # Limit to 3 domains
        print(f"  Trying RSS for {domain}...")
        articles = try_find_rss_feed(domain, max_articles)
        if articles:
            print(f"  ✅ Found {len(articles)} articles via RSS")
            all_articles.extend(articles)
        else:
            print(f"  ❌ No RSS feed found")
    
    return all_articles
