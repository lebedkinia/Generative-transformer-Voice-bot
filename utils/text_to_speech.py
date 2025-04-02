from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

def text_to_speech1(text, filename="response.ogg", voice_ai="Ahmad-PlayAI"):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.audio.speech.create(
        model="playai-tts-arabic",
        voice=voice_ai,
        input=text,
        response_format="wav"
    )
    
    audio_content = response.read()
    
    with open(filename, "wb") as f:
        f.write(audio_content)
        
    return filename