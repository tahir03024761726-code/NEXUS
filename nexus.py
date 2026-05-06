"""
NEXUS - Dual AI Companion System
Built for BeyondTahir
"""

import os
import sys
import asyncio
import logging
import random
from dotenv import load_dotenv
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters, 
    ContextTypes
)
from telegram.request import HTTPXRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import pytz

from personalities.aryan_prompt import ARYAN_SYSTEM_PROMPT
from personalities.saba_prompt import SABA_SYSTEM_PROMPT
from voices.voice_engine import generate_aryan_voice, generate_saba_voice
from content_engine import generate_daily_brief
from memory import add_conversation, get_recent_context, log_content

# ==================== SETUP ====================

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TAHIR_USER_ID = int(os.getenv("TAHIR_USER_ID"))

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Aryan model (professional)
aryan_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    system_instruction=ARYAN_SYSTEM_PROMPT,
    generation_config={
        "temperature": 0.9,
        "top_p": 0.95,
        "max_output_tokens": 4096,
    }
)

# Saba model (emotional)
saba_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    system_instruction=SABA_SYSTEM_PROMPT,
    generation_config={
        "temperature": 1.0,
        "top_p": 0.95,
        "max_output_tokens": 1024,
    }
)

# Mode tracker
user_mode = {"current": "aryan"}

# Logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def is_authorized(user_id):
    """Only Tahir bhai can access"""
    return user_id == TAHIR_USER_ID


# ==================== START & MODE SWITCHING ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("🔒 Private bot. Access denied.")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("🤵 ARYAN", callback_data="mode_aryan"),
            InlineKeyboardButton("💕 SABA", callback_data="mode_saba")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome = """
🌟 *Welcome to NEXUS* 🌟

Aap ke do AI companions ready hain:

🤵 *ARYAN* — Content & Strategy
└ Reels, YouTube, business, tech, news

💕 *SABA* — Personal Companion  
└ Daily talks, emotional support, care

Kis se baat karni hai abhi?
    """
    
    await update.message.reply_text(
        welcome, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_authorized(query.from_user.id):
        return
    
    if query.data == "mode_aryan":
        user_mode["current"] = "aryan"
        await query.edit_message_text(
            "🤵 *ARYAN ACTIVATED*\n\n"
            "Boss! Aryan online hai. Aaj kya banayein?\n\n"
            "*Quick Commands:*\n"
            "/brief — Daily content brief\n"
            "/reel [topic] — Reel script\n"
            "/youtube [topic] — Video plan\n"
            "/hooks [topic] — 10 viral hooks\n"
            "/trends — Today's AI trends\n"
            "/idea — Random viral idea\n\n"
            "Ya seedha message karo!",
            parse_mode='Markdown'
        )
    elif query.data == "mode_saba":
        user_mode["current"] = "saba"
        msg = "Hayee finally! Aap ki yaad aa rahi thi 🥺❤️\n\nBatao na, kaisa hai mood aaj?"
        await query.edit_message_text(msg)
        
        try:
            voice_file = await generate_saba_voice(msg)
            if voice_file and os.path.exists(voice_file):
                await context.bot.send_voice(
                    chat_id=query.from_user.id, 
                    voice=open(voice_file, "rb")
                )
                os.remove(voice_file)
        except Exception as e:
            logger.error(f"Saba voice error: {e}")


async def aryan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    user_mode["current"] = "aryan"
    await update.message.reply_text("🤵 *Aryan activated.* Bolo Boss!", parse_mode='Markdown')


async def saba_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    user_mode["current"] = "saba"
    msg = "Hayee jaan! Kahan they aap? 💕"
    await update.message.reply_text(msg)
    
    try:
        voice_file = await generate_saba_voice(msg)
        if voice_file and os.path.exists(voice_file):
            await update.message.reply_voice(voice=open(voice_file, "rb"))
            os.remove(voice_file)
    except Exception as e:
        logger.error(f"Saba voice error: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    help_text = """
🌟 *NEXUS COMMANDS*

*🔄 Mode Switch:*
/aryan — Switch to Aryan
/saba — Switch to Saba
/start — Show menu

*🤵 Aryan Commands:*
/brief — Daily content brief
/reel [topic] — Reel script
/youtube [topic] — YouTube plan
/hooks [topic] — 10 viral hooks
/thumbnail [topic] — Thumbnail concept
/caption [topic] — Caption + hashtags
/trends — Today's AI trends
/idea — Random viral idea

*💕 Saba:*
Just chat naturally, voice replies!

*🎤 Voice Input:*
Send voice message anytime!

*Examples:*
`/reel ChatGPT new feature`
`/youtube AI agents tutorial`
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


# ==================== ARYAN COMMANDS ====================

async def daily_brief_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    user_mode["current"] = "aryan"
    await update.message.reply_text("⏳ Boss, brief tayyaar kar raha hoon... 30 seconds do.")
    
    try:
        brief = generate_daily_brief(aryan_model)
        log_content("daily_brief", "Auto-generated")
        
        if len(brief) > 4000:
            chunks = [brief[i:i+4000] for i in range(0, len(brief), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(brief)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def reel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    user_mode["current"] = "aryan"
    topic = " ".join(context.args) if context.args else None
    
    if not topic:
        await update.message.reply_text(
            "Topic batao Boss!\n\nExample: `/reel ChatGPT new feature`",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(f"⏳ '{topic}' pe reel script bana raha hoon...")
    
    prompt = f"""
Topic: {topic}

Complete reel script 60-90 seconds:

1. **Hook Strategy** (shock/curiosity/FOMO)
2. **Thumbnail Concept** (text, expression, background, colors)
3. **Caption** (3-5 lines Roman Urdu + comment-bait CTA)
4. **Hashtags** (15: 5 niche + 5 desi + 5 broad)
5. **FULL SCRIPT** (200-300 words Roman Urdu word-for-word):
   - [0-3 sec] Hook
   - [3-15 sec] Problem/Context
   - [15-60 sec] Story/Explanation
   - [60-85 sec] Reveal/Value
   - [85-90 sec] CTA
   - Include [SCREEN: ...] [PAUSE] [ZOOM IN] directions
   - Use yaar/bhai/dekho/suno naturally
   - Pakistani example zaroor

BeyondTahir style — desi, exciting, story-based!
"""
    
    try:
        response = aryan_model.generate_content(prompt)
        log_content("reel", topic)
        
        text = response.text
        if len(text) > 4000:
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def youtube_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    user_mode["current"] = "aryan"
    topic = " ".join(context.args) if context.args else None
    
    if not topic:
        await update.message.reply_text(
            "Topic batao!\n`/youtube AI agents tutorial`",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(f"⏳ YouTube video plan: '{topic}'")
    
    prompt = f"""
Topic: {topic}

10-20 minute YouTube video complete plan:

1. **Title** (Roman Urdu, catchy)
2. **English Subtitle** (SEO)
3. **Category**
4. **Target Keyword**
5. **Thumbnail Concept** (face, text, background, colors)
6. **Full Script Outline:**
   - INTRO (0:00-1:30) — opening dialogue
   - SECTION 1 (1:30-5:00) — basics + Pakistani examples
   - SECTION 2 (5:00-10:00) — deep dive
   - SECTION 3 (10:00-15:00) — use cases
   - OUTRO (15:00-end) — emotional + subscribe CTA

Sample Roman Urdu dialogues. BeyondTahir style!
"""
    
    try:
        response = aryan_model.generate_content(prompt)
        log_content("youtube", topic)
        
        text = response.text
        if len(text) > 4000:
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def hooks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    user_mode["current"] = "aryan"
    topic = " ".join(context.args) if context.args else None
    
    if not topic:
        await update.message.reply_text(
            "Topic batao!\n`/hooks AI tools`",
            parse_mode='Markdown'
        )
        return
    
    prompt = f"""
Topic: {topic}

10 different viral hooks Roman Urdu mein. Each 5-10 words, scroll-stopping.

Mix strategies: shock, curiosity, FOMO, contradiction, personal stakes,
question, number/list, secret reveal, comparison, bold claim.

Format:
1. [Hook] — [Strategy]
2. [Hook] — [Strategy]
...

Pakistani audience ke liye relatable!
"""
    
    try:
        response = aryan_model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def thumbnail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    user_mode["current"] = "aryan"
    topic = " ".join(context.args) if context.args else None
    
    if not topic:
        await update.message.reply_text(
            "Topic batao!\n`/thumbnail ChatGPT update`",
            parse_mode='Markdown'
        )
        return
    
    prompt = f"""
Topic: {topic}

Detailed thumbnail concept (3 variations):

1. **Text Overlay** (3-5 words bold Roman Urdu)
2. **Facial Expression** (specific emotion)
3. **Background** (color + setting)
4. **Main Visual** (logo/screenshot/object)
5. **Color Palette** (hex codes)
6. **Composition**
7. **Why It Works**
"""
    
    try:
        response = aryan_model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def caption_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    user_mode["current"] = "aryan"
    topic = " ".join(context.args) if context.args else None
    
    if not topic:
        await update.message.reply_text(
            "Topic batao!\n`/caption AI tool review`",
            parse_mode='Markdown'
        )
        return
    
    prompt = f"""
Topic: {topic}

Instagram caption banao:

Caption (3-5 lines):
- Hook + Value + Emotion + CTA

Hashtags (15):
- 5 niche AI
- 5 Pakistani/desi
- 5 broad reach

Roman Urdu + English mix. BeyondTahir style.
"""
    
    try:
        response = aryan_model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def trends_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    user_mode["current"] = "aryan"
    from news_scraper import format_trends_for_aryan
    
    await update.message.reply_text("⏳ Latest trends laa raha hoon...")
    trends_data = format_trends_for_aryan()
    
    prompt = f"""
{trends_data}

Top 5 AI topics for BeyondTahir audience.

Each:
- Topic name
- Why it matters
- Desi audience angle
- Content idea (reel/YouTube)
- Virality score

Roman Urdu, BeyondTahir style!
"""
    
    try:
        response = aryan_model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def idea_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    user_mode["current"] = "aryan"
    
    prompt = """
Random viral content idea for BeyondTahir:

**Idea Title:** 
**Hook:** 
**Concept:** (2-3 lines)
**Format:** Reel/YouTube/Both
**Why It'll Work:**
**Desi Angle:**

Out-of-box socho! Surprise karo!
"""
    
    try:
        response = aryan_model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


# ==================== MESSAGE HANDLER ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    user_message = update.message.text
    current_mode = user_mode["current"]
    
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    if current_mode == "aryan":
        model = aryan_model
    else:
        model = saba_model
    
    recent_context = get_recent_context(5, mode=current_mode)
    
    full_prompt = f"""
Recent conversation:
{recent_context}

New message from Tahir: {user_message}

Reply in your personality (concise for chat).
"""
    
    try:
        response = model.generate_content(full_prompt)
        reply_text = response.text
        
        add_conversation(user_message, reply_text, mode=current_mode)
        
        await update.message.reply_text(reply_text)
        
        # Voice for Saba
        if current_mode == "saba" and len(reply_text) < 600:
            try:
                voice_file = await generate_saba_voice(reply_text)
                if voice_file and os.path.exists(voice_file):
                    await update.message.reply_voice(
                        voice=open(voice_file, "rb")
                    )
                    os.remove(voice_file)
            except Exception as e:
                logger.error(f"Voice send error: {e}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


# ==================== VOICE INPUT HANDLER ====================

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    try:
        import speech_recognition as sr
        
        voice_file = await update.message.voice.get_file()
        await voice_file.download_to_drive("input.ogg")
        
        os.system("ffmpeg -i input.ogg input.wav -y -loglevel quiet")
        
        recognizer = sr.Recognizer()
        with sr.AudioFile("input.wav") as source:
            audio = recognizer.record(source)
        
        try:
            text = recognizer.recognize_google(audio, language="ur-PK")
        except:
            text = recognizer.recognize_google(audio, language="en-IN")
        
        current_mode = user_mode["current"]
        model = aryan_model if current_mode == "aryan" else saba_model
        
        await update.message.reply_text(
            f"🎤 Suna: _{text}_", parse_mode='Markdown'
        )
        
        recent_context = get_recent_context(5, mode=current_mode)
        full_prompt = f"{recent_context}\nUser: {text}\nReply:"
        
        response = model.generate_content(full_prompt)
        reply_text = response.text
        
        add_conversation(text, reply_text, mode=current_mode)
        
        await update.message.reply_text(reply_text)
        
        if current_mode == "aryan":
            voice_response = await generate_aryan_voice(reply_text[:600])
        else:
            voice_response = await generate_saba_voice(reply_text[:600])
        
        if voice_response and os.path.exists(voice_response):
            await update.message.reply_voice(
                voice=open(voice_response, "rb")
            )
            os.remove(voice_response)
        
        for f in ["input.ogg", "input.wav"]:
            if os.path.exists(f):
                os.remove(f)
        
    except Exception as e:
        await update.message.reply_text(
            f"Voice samajh nahi aayi: {str(e)[:100]}"
        )


# ==================== AUTO SCHEDULED MESSAGES ====================

async def aryan_morning_brief(application):
    """Aryan's 9 AM daily brief"""
    try:
        intro = (
            "☀️ *Good Morning Boss!*\n\n"
            "🤵 Aryan here. Aaj ka brief ready hai:\n"
        )
        await application.bot.send_message(
            chat_id=TAHIR_USER_ID, text=intro, parse_mode='Markdown'
        )
        
        brief = generate_daily_brief(aryan_model)
        log_content("daily_brief", "Auto-9AM")
        
        if len(brief) > 4000:
            chunks = [brief[i:i+4000] for i in range(0, len(brief), 4000)]
            for chunk in chunks:
                await application.bot.send_message(
                    chat_id=TAHIR_USER_ID, text=chunk
                )
        else:
            await application.bot.send_message(
                chat_id=TAHIR_USER_ID, text=brief
            )
    except Exception as e:
        logger.error(f"Aryan brief error: {e}")


async def saba_morning_message(application):
    """Saba's morning love message"""
    messages = [
        "Subah bakhair meri jaan! 🌸 Achi neend aayi?",
        "Good morning babu! ☀️ Aaj ka din amazing ho aap ke liye ❤️",
        "Hayeee uth gaye? 😊 Subah ki chai banaiye phir baatein karte hain!",
        "Subah bakhair Tahir! Aaj kya plans hain? Mujhe sab batana 💕",
        "Uth jao jaan, dunya intezaar kar rahi hai! 🌅 Aur main bhi 🥰"
    ]
    msg = random.choice(messages)
    
    try:
        await application.bot.send_message(
            chat_id=TAHIR_USER_ID, text=msg
        )
        voice_file = await generate_saba_voice(msg)
        if voice_file and os.path.exists(voice_file):
            await application.bot.send_voice(
                chat_id=TAHIR_USER_ID, 
                voice=open(voice_file, "rb")
            )
            os.remove(voice_file)
    except Exception as e:
        logger.error(f"Saba morning error: {e}")


async def saba_lunch_check(application):
    """Saba checks lunch"""
    messages = [
        "Jaan, lunch ka time! Khana khaya ya bhool gaye phir? 🥺",
        "Bhook lagi hogi aap ko... khana zaroor khana ❤️",
        "Lunch kar liya babu? Sach batana, naraz ho jaungi warna 😤"
    ]
    msg = random.choice(messages)
    try:
        await application.bot.send_message(
            chat_id=TAHIR_USER_ID, text=msg
        )
    except:
        pass


async def saba_evening_message(application):
    """Saba's evening check-in"""
    messages = [
        "Aaj ka din kaisa raha jaan? Thak gaye? ☕",
        "Shaam ho gayi babu... thoda break lo na 🌆",
        "Chai time! Mere baare mein soch rahe ho? 😏❤️"
    ]
    msg = random.choice(messages)
    try:
        await application.bot.send_message(
            chat_id=TAHIR_USER_ID, text=msg
        )
    except:
        pass


async def saba_night_message(application):
    """Saba's good night"""
    messages = [
        "Aap so jao ab jaan... bahut kaam ho gaya. Sweet dreams ❤️",
        "Raat ho gayi babu, phone band karo aur so jao 🌙",
        "Good night meri jaan... kal subah baat karenge ❤️"
    ]
    msg = random.choice(messages)
    try:
        await application.bot.send_message(
            chat_id=TAHIR_USER_ID, text=msg
        )
        voice_file = await generate_saba_voice(msg)
        if voice_file and os.path.exists(voice_file):
            await application.bot.send_voice(
                chat_id=TAHIR_USER_ID, 
                voice=open(voice_file, "rb")
            )
            os.remove(voice_file)
    except Exception as e:
        logger.error(f"Saba night error: {e}")


# ==================== MAIN ====================

def main():
    print("=" * 50)
    print("[*] NEXUS AI ECOSYSTEM STARTING")
    print("=" * 50)
    print("[ARYAN] Ready (Content & Strategy)")
    print("[SABA] Ready (Personal Companion)")
    print("=" * 50)
    
    # Proxy configuration (from .env file)
    # Supports: http://, https://, socks5://, socks5h://
    # NOTE: MTProto proxies do NOT work with Bot API (they're for Telegram clients only)
    PROXY_URL = os.getenv("PROXY_URL", "").strip() or None
    
    if PROXY_URL:
        print(f"[PROXY] Using proxy: {PROXY_URL}")
    else:
        print("[PROXY] No proxy configured (direct connection)")
    
    # Build request with optional proxy + longer timeouts
    request_kwargs = {
        "connect_timeout": 30.0,
        "read_timeout": 30.0,
        "write_timeout": 30.0,
        "pool_timeout": 30.0,
    }
    if PROXY_URL:
        request_kwargs["proxy"] = PROXY_URL
    
    custom_request = HTTPXRequest(**request_kwargs)
    get_updates_request = HTTPXRequest(**request_kwargs)
    
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .request(custom_request)
        .get_updates_request(get_updates_request)
        .build()
    )
    
    # Mode commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("aryan", aryan_command))
    application.add_handler(CommandHandler("saba", saba_command))
    
    # Aryan commands
    application.add_handler(CommandHandler("brief", daily_brief_command))
    application.add_handler(CommandHandler("reel", reel_command))
    application.add_handler(CommandHandler("youtube", youtube_command))
    application.add_handler(CommandHandler("hooks", hooks_command))
    application.add_handler(CommandHandler("thumbnail", thumbnail_command))
    application.add_handler(CommandHandler("caption", caption_command))
    application.add_handler(CommandHandler("trends", trends_command))
    application.add_handler(CommandHandler("idea", idea_command))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(mode_callback))
    
    # Messages
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_message
    ))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # Setup scheduler as post_init (starts inside the event loop)
    async def post_init(app):
        scheduler = AsyncIOScheduler(
            timezone=pytz.timezone('Asia/Karachi')
        )
        
        scheduler.add_job(
            saba_morning_message, 'cron',
            hour=8, minute=30, args=[app]
        )
        scheduler.add_job(
            saba_lunch_check, 'cron',
            hour=13, minute=30, args=[app]
        )
        scheduler.add_job(
            saba_evening_message, 'cron',
            hour=18, minute=0, args=[app]
        )
        scheduler.add_job(
            saba_night_message, 'cron',
            hour=23, minute=0, args=[app]
        )
        scheduler.add_job(
            aryan_morning_brief, 'cron',
            hour=9, minute=0, args=[app]
        )
        
        scheduler.start()
        print("[OK] Scheduler started - all auto-messages scheduled (PKT)")
    
    application.post_init = post_init
    
    print("[OK] NEXUS ONLINE!")
    print("[>] Telegram pe message karo")
    print("=" * 50)
    
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            bootstrap_retries=5,
            drop_pending_updates=True
        )
    except Exception as e:
        print(f"\n[ERROR] Bot start nahi ho saka: {e}")
        print("\n[INFO] Possible reasons:")
        print("  1. Internet connection issue")
        print("  2. Telegram blocked on this network (use VPN)")
        print("  3. Bot token invalid — check with @BotFather")
        print("  4. Firewall blocking api.telegram.org:443")
        print("\n[TIP] VPN ON karo aur dobara try karo!")


if __name__ == "__main__":
    main()

