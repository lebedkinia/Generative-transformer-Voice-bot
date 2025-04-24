from deep_translator import GoogleTranslator
import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv()


def get_image_description(image_path):
    try:
        # Загружаем изображение
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        HUGGINGFACE_API_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN')
        # Запрос к HuggingFace API
        response = requests.post(
            "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base",
            headers={"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"},
            data=image_bytes
        )

        # Проверка ответа
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                description_en = result[0].get('generated_text', '')
                if description_en:
                    # Перевод на русский
                    return GoogleTranslator(source='auto', target='ru').translate(description_en)
        elif response.status_code == 503:
            # Модель может загружаться
            raise Exception("Сервис временно недоступен. Попробуйте позже.")

        raise Exception(
            f"Не удалось обработать изображение. Код ошибки: {response.status_code}")

    except Exception as e:
        logging.error(f"Ошибка в get_image_description: {str(e)}")
        raise
