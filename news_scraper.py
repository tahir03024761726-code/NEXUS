import feedparser

AI_FEEDS = [
    "https://www.understandingai.org/feed",
    "https://www.therundown.ai/feed",
    "https://tldr.tech/api/rss/ai",
    "https://www.marketingaiinstitute.com/blog/rss.xml",
]


def fetch_ai_trends(limit=10):
    """Fetch latest AI news from RSS feeds"""
    all_articles = []
    
    for feed_url in AI_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                all_articles.append({
                    "title": entry.get("title", "No title"),
                    "summary": entry.get("summary", "")[:300],
                    "link": entry.get("link", ""),
                    "source": feed.feed.get("title", "Unknown")
                })
        except Exception as e:
            print(f"Error fetching {feed_url}: {e}")
    
    return all_articles[:limit]


def format_trends_for_aryan():
    """Format trends for content brief"""
    articles = fetch_ai_trends(10)
    if not articles:
        return "Aaj koi naya trend nahi mila."
    
    formatted = "TODAY'S AI TRENDS:\n\n"
    for i, article in enumerate(articles, 1):
        formatted += f"{i}. {article['title']}\n"
        formatted += f"   Source: {article['source']}\n"
        formatted += f"   Summary: {article['summary'][:150]}...\n\n"
    
    return formatted


if __name__ == "__main__":
    print(format_trends_for_aryan())
