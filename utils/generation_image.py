import logging
from gradio_client import Client
import os

def generate_image(prompt):
    try:
        client = Client("lalashechka/FLUX_1")
        result = client.predict(
            prompt=prompt,
            task="FLUX.1 [schnell]",
            api_name="/flip_text"
        )
        
        # Обработка результата
        if isinstance(result, str):
            if result.startswith(('http://', 'https://')):
                return {"type": "url", "content": result}
            elif os.path.exists(result):
                return {"type": "file", "content": result}
        
        return None
        
    except Exception as e:
        logging.error(f"Image generation error: {str(e)}", exc_info=True)
        return None