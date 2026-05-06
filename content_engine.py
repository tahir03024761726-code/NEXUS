from news_scraper import format_trends_for_aryan
from datetime import datetime
import pytz


def generate_daily_brief(model):
    """Generate complete daily content brief"""
    
    pkt = pytz.timezone('Asia/Karachi')
    today = datetime.now(pkt).strftime("%d %B %Y")
    
    trends = format_trends_for_aryan()
    
    brief_prompt = f"""
{trends}

---

Aaj ki date: {today}

Boss ke liye complete daily content brief banao is exact format mein:

═══════════════════════════════════════════
       BEYONDTAHIR DAILY CONTENT BRIEF
═══════════════════════════════════════════
📅 Date: {today}
⏰ Generated: 9:00 AM PKT
🎯 Today's Theme: [one-line theme]

1️⃣ TRENDING TODAY — TOP 3 AI TOPICS
[Har topic: name, why it matters, audience angle, content angle, source, virality]

2️⃣ REEL 1 — AI NEWS REEL (60-90 sec)
- Topic
- Hook strategy
- Thumbnail concept (text, expression, background, colors)
- Caption (3-5 lines + CTA)
- 15 hashtags
- FULL SCRIPT (200-300 words Roman Urdu with [SCREEN] directions)

3️⃣ REEL 2 — AI TOOL/TUTORIAL REEL (60-90 sec)
[Same structure, practical tool]

4️⃣ LONG YOUTUBE VIDEO IDEA (10-20 min)
- Title (Roman Urdu)
- English subtitle
- Category
- Thumbnail concept
- Full outline with timestamps and sample dialogues

5️⃣ NEWSLETTER/ARTICLE IDEA
- Title, platform, sections, hook paragraph

6️⃣ QUICK WINS — 3 backup ideas

Sab kuch BeyondTahir style mein — desi, exciting, story-based!
"""
    
    response = model.generate_content(brief_prompt)
    return response.text
