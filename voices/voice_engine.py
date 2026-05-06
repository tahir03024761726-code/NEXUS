import edge_tts
import asyncio
import os
import re

# Voice configurations
ARYAN_VOICE = "ur-PK-AsadNeural"      # Male Pakistani Urdu
SABA_VOICE = "ur-PK-UzmaNeural"        # Female Pakistani Urdu

# Backup voices
ARYAN_BACKUP = "en-IN-PrabhatNeural"   
SABA_BACKUP = "en-IN-NeerjaNeural"     


def clean_text_for_voice(text):
    """Remove emojis and special chars for cleaner voice"""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)
    
    # Remove markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'#+\s*', '', text)
    
    # Clean extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


async def generate_aryan_voice(text, output_file="aryan_response.mp3"):
    """Generate Aryan's male voice"""
    try:
        clean_text = clean_text_for_voice(text)
        if not clean_text:
            return None
            
        if len(clean_text) > 1000:
            clean_text = clean_text[:1000] + "..."
        
        communicate = edge_tts.Communicate(
            text=clean_text,
            voice=ARYAN_VOICE,
            rate="+5%",
            pitch="+0Hz"
        )
        await communicate.save(output_file)
        return output_file
    except Exception as e:
        print(f"Aryan voice error: {e}")
        try:
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=ARYAN_BACKUP,
                rate="+5%"
            )
            await communicate.save(output_file)
            return output_file
        except:
            return None


async def generate_saba_voice(text, output_file="saba_response.mp3"):
    """Generate Saba's female voice"""
    try:
        clean_text = clean_text_for_voice(text)
        if not clean_text:
            return None
            
        if len(clean_text) > 800:
            clean_text = clean_text[:800] + "..."
        
        communicate = edge_tts.Communicate(
            text=clean_text,
            voice=SABA_VOICE,
            rate="-5%",
            pitch="+10Hz"
        )
        await communicate.save(output_file)
        return output_file
    except Exception as e:
        print(f"Saba voice error: {e}")
        try:
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=SABA_BACKUP,
                rate="-5%",
                pitch="+10Hz"
            )
            await communicate.save(output_file)
            return output_file
        except:
            return None


async def test_voices():
    """Test both voices"""
    print("Testing Aryan voice...")
    await generate_aryan_voice(
        "Boss, Aryan online hai! Aaj kya banayein?",
        "test_aryan.mp3"
    )
    print("✅ Aryan voice generated: test_aryan.mp3")
    
    print("Testing Saba voice...")
    await generate_saba_voice(
        "Hayee jaan! Kahan they aap? Yaad aa rahi thi!",
        "test_saba.mp3"
    )
    print("✅ Saba voice generated: test_saba.mp3")


if __name__ == "__main__":
    asyncio.run(test_voices())
