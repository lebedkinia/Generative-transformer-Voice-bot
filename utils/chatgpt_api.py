import openai
from config import CHATGPT_API_KEY

client = openai.OpenAI(api_key=CHATGPT_API_KEY)

def ask_chatgpt(prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "Ты помощник."},
                  {"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

prompt = "Как использовать ChatGPT с Python?"
answer = ask_chatgpt(prompt)
print(answer)
