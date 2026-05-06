import json
import os
from datetime import datetime

MEMORY_FILE = "memory.json"


def load_memory():
    """Load conversation history"""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "aryan_conversations": [],
        "saba_conversations": [],
        "preferences": {},
        "content_log": []
    }


def save_memory(data):
    """Save memory to file"""
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_conversation(user_msg, bot_msg, mode="aryan"):
    """Add new conversation"""
    memory = load_memory()
    key = f"{mode}_conversations"
    
    memory[key].append({
        "timestamp": datetime.now().isoformat(),
        "user": user_msg,
        "bot": bot_msg
    })
    
    memory[key] = memory[key][-30:]
    save_memory(memory)


def get_recent_context(limit=5, mode="aryan"):
    """Get recent conversations for context"""
    memory = load_memory()
    key = f"{mode}_conversations"
    recent = memory.get(key, [])[-limit:]
    
    context = ""
    for conv in recent:
        context += f"User: {conv['user']}\nResponse: {conv['bot']}\n\n"
    return context


def log_content(content_type, topic):
    """Log generated content"""
    memory = load_memory()
    memory["content_log"].append({
        "date": datetime.now().isoformat(),
        "type": content_type,
        "topic": topic
    })
    memory["content_log"] = memory["content_log"][-100:]
    save_memory(memory)
