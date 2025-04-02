from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

def transcribe_audio(filename):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    with open(filename, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(filename, file.read()),
            model="whisper-large-v3-turbo",
            language="ru",
            response_format="verbose_json",
        )
        print(transcription.text)
        return transcription.text
