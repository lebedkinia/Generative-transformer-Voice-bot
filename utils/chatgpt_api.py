from groq import Groq
from utils.config import GROQ_API_KEY


def ask(content: str):
    client = Groq(api_key=GROQ_API_KEY)

    completion = client.chat.completions.create(
        model="gemma2-9b-it",
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
