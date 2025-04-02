from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

def ask(content: str):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    completion = client.chat.completions.create(
        model="qwen-2.5-32b",
        messages=[
            {
                "role": "user",
                "content": content
            }
        ],
        temperature=0.6,
        max_completion_tokens=4096,
        top_p=0.95,
        stream=False,
        stop=None,
    )


    print(completion.choices[0].message.to_dict()["content"])
    return completion.choices[0].message.to_dict()["content"]
