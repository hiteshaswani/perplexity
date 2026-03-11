"""
Perplexity Clone - Simplified Main Application
Orchestrates the research pipeline
"""

import asyncio
import json
from datetime import datetime

# Import our modules
from ai import generate_search_queries, summarize_page, generate_answer, validate_answer, fact_check_answer
from search import search_web
from crawler import crawl_pages
from rss_parser import fetch_rss_fallback

# Configuration
#MAX_SEARCH_QUERIES = 5
#MAX_RESULTS_PER_QUERY = 5
MAX_SEARCH_QUERIES = 1
MAX_RESULTS_PER_QUERY = 2


def initial_research(query: str) -> dict:
    """
    Step 1: Initial research phase
    - Generate queries
    - Search web
    - Crawl pages (with RSS fallback)
    - Summarize content
    - Generate answer
    """
    print("=" * 60)
    print(f"🔬 RESEARCH QUERY: {query}")
    print("=" * 60)
    
    # 1. Generate search queries
    queries = generate_search_queries(query, MAX_SEARCH_QUERIES)
    
    # 2. Search web
    search_results = search_web(queries, MAX_RESULTS_PER_QUERY)
    
    if not search_results:
        return {"error": "No search results found"}
    
    # 3. Crawl pages
    urls = [r['url'] for r in search_results]
    pages = asyncio.run(crawl_pages(urls))
    
    # 4. Try RSS fallback if too few pages
    if len(pages) < 5:
        failed_urls = [r['url'] for r in search_results if r['url'] not in [p['url'] for p in pages]]
        rss_articles = fetch_rss_fallback(failed_urls, max_articles=3)
        pages.extend(rss_articles)
    
    if not pages:
        return {"error": "Could not fetch any content"}
    
    print(f"\n📊 Total pages collected: {len(pages)}")
    
    # 5. Summarize pages
    print(f"\n📝 Summarizing {len(pages)} pages with AI...")
    summaries = []
    
    for i, page in enumerate(pages, 1):
        print(f"  [{i}/{len(pages)}] {page.get('title', page['url'][:50])}...")
        
        if not page.get('content'):
            continue
        
        summary = summarize_page(page['content'], query, page.get('title', ''))
        
        if summary and "no relevant" not in summary.lower():
            summaries.append({
                'title': page.get('title', 'Untitled'),
                'url': page['url'],
                'summary': summary
            })
    
    print(f"  ✅ {len(summaries)} relevant summaries")
    
    if not summaries:
        return {"error": "No relevant content found"}
    
    # 6. Generate answer
    answer = generate_answer(query, summaries)
    
    return {
        "query": query,
        "sub_queries": queries,
        "sources": summaries,
        "answer": answer
    }


def validation_and_followup(initial_result: dict) -> dict:
    """
    Step 2: Validation and follow-up phase
    - Validate answer completeness
    - If incomplete, search for missing topics
    - Regenerate complete answer
    - Fact-check answer against sources
    """
    query = initial_result['query']
    answer = initial_result['answer']
    sources = initial_result.get('sources', [])
    
    # Validate answer completeness
    validation = validate_answer(query, answer)
    
    # If incomplete, do follow-up research
    missing_topics = validation.get('missing_topics', [])
    
    if missing_topics:
        print(f"\n🔄 Searching for missing topics: {', '.join(missing_topics)}")
        
        additional_summaries = []
        
        for topic in missing_topics[:3]:  # Limit to 3 topics
            print(f"\n  🔎 Follow-up: {topic}")
            
            # Search for this specific topic
            follow_query = f"{query} {topic}"
            follow_queries = generate_search_queries(follow_query, 1)
            
            if not follow_queries:
                continue
            
            # Search and crawl
            follow_results = search_web([follow_queries[0]], 3)
            
            if follow_results:
                follow_urls = [r['url'] for r in follow_results]
                follow_pages = asyncio.run(crawl_pages(follow_urls))
                
                # Summarize
                for page in follow_pages:
                    if page.get('content'):
                        summary = summarize_page(page['content'], follow_query, page.get('title', ''))
                        
                        if summary and "no relevant" not in summary.lower():
                            additional_summaries.append({
                                'title': page.get('title', 'Untitled'),
                                'url': page['url'],
                                'summary': summary
                            })
        
        if additional_summaries:
            print(f"\n✅ Found {len(additional_summaries)} additional sources")
            
            # Combine sources
            sources = initial_result['sources'] + additional_summaries
            
            # Regenerate answer
            print(f"\n♻️  Regenerating answer with complete information...")
            answer = generate_answer(query, sources)
            validation = {"complete": True, "missing_topics": [], "followup_completed": True}
    
    # Fact-check the answer (always run after validation)
    fact_check = fact_check_answer(answer, sources)
    
    # Return final result
    return {
        "query": query,
        "sub_queries": initial_result['sub_queries'],
        "sources": sources[:12],
        "answer": answer,
        "validation": validation,
        "fact_check": fact_check
    }


def run_search(query: str) -> dict:
    """
    Main pipeline - orchestrates both phases
    """
    # Phase 1: Initial research
    result = initial_research(query)
    
    if 'error' in result:
        return result
    
    # Phase 2: Validation and follow-up
    final_result = validation_and_followup(result)
    
    return final_result


def pretty_print(result: dict):
    """Display result nicely."""
    print("\n" + "=" * 60)
    print("📊 FINAL ANSWER")
    print("=" * 60)
    print(result.get('answer', 'No answer'))
    
    # Display validation status
    validation = result.get('validation', {})
    if validation:
        print("\n" + "=" * 60)
        print("✓ VALIDATION")
        print("=" * 60)
        if validation.get('complete'):
            print("✅ Complete" + (" (after follow-up)" if validation.get('followup_completed') else ""))
        else:
            missing = validation.get('missing_topics', [])
            print(f"⚠️  Missing topics: {', '.join(missing)}")
    
    # Display fact-check results
    fact_check = result.get('fact_check', {})
    if fact_check:
        print("\n" + "=" * 60)
        print("🔬 FACT CHECK")
        print("=" * 60)
        verdict = fact_check.get('verdict', 'unknown')
        score = fact_check.get('accuracy_score', 0)
        
        verdict_emoji = {
            'accurate': '✅',
            'mostly_accurate': '✓',
            'partially_accurate': '⚠️',
            'inaccurate': '❌'
        }
        
        print(f"{verdict_emoji.get(verdict, '❓')} {verdict.upper().replace('_', ' ')} (Score: {score}/100)")
        
        unsupported = fact_check.get('unsupported_claims', [])
        contradicted = fact_check.get('contradicted_claims', [])
        issues = fact_check.get('issues', [])
        
        if unsupported:
            print(f"\n⚠️  Unsupported claims ({len(unsupported)}):")
            for claim in unsupported[:3]:
                print(f"   • {claim}")
        
        if contradicted:
            print(f"\n❌ Contradicted claims ({len(contradicted)}):")
            for claim in contradicted[:3]:
                print(f"   • {claim}")
        
        if issues:
            print(f"\n📝 Issues ({len(issues)}):")
            for issue in issues[:3]:
                print(f"   • {issue}")
    
    print("\n" + "=" * 60)
    print(f"📚 SOURCES ({len(result.get('sources', []))})")
    print("=" * 60)
    for i, src in enumerate(result.get('sources', []), 1):
        print(f"\n[{i}] {src['title']}")
        print(f"    🔗 {src['url']}")
        print(f"    📝 {src['summary'][:100]}...")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        
        # Run search
        result = run_search(query)
        
        # Display
        pretty_print(result)
        
        # Save to file
        with open('result.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n💾 Results saved to result.json")
    else:
        print("Usage: python app_simple.py 'your question here'")
