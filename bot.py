import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InputFile
from dotenv import load_dotenv
from utils.speech_to_text import transcribe_audio
from utils.chatgpt_api import ask
from utils.text_to_speech import text_to_speech1
from utils.generation_image import generate_image
from utils.description_image import get_image_description
import os
import tempfile
import requests
from io import BytesIO

logging.basicConfig(level=logging.INFO)
load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()
router = Router()

user_preferences = {}
image_generation_mode = {}
photo_description_mode = {}

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="🎨 Сгенерировать изображение")],
            [KeyboardButton(text="📷 Описать фото")]  
        ],
        resize_keyboard=True,
        persistent=True
    )

def get_settings_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎧 Всегда отвечать голосом")],
            [KeyboardButton(text="📄 Всегда отвечать текстом")],
            [KeyboardButton(text="🤖 Выбрать голос бота")],
            [KeyboardButton(text="↩️ Назад")]
        ],
        resize_keyboard=True,
        persistent=True
    )

def get_voice_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Ахмед")],
            [KeyboardButton(text="Кхалид")],
            [KeyboardButton(text="Амира")],
            [KeyboardButton(text="↩️ Назад")]
        ],
        resize_keyboard=True,
        persistent=True
    )

async def download_image(url: str):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BytesIO(response.content)
    except Exception as e:
        logging.error(f"Ошибка загрузки изображения: {e}")
        return None

@router.message(CommandStart())
async def start_command(message: Message):
    user_preferences[message.from_user.id] = {
        "output": "text",
        "voice": "Ahmad-PlayAI"
    }
    image_generation_mode[message.from_user.id] = False
    await message.answer(
        "Привет! Я многофункциональный бот:\n"
        "- Отвечаю на вопросы текстом/голосом\n"
        "- Генерирую изображения по запросу\n\n"
        "Выбери действие:",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "🎨 Сгенерировать изображение")
async def enable_image_generation(message: Message):
    image_generation_mode[message.from_user.id] = True
    await message.answer(
        "Режим генерации изображения активирован. Отправьте текстовый промпт для генерации изображения:",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "⚙️ Настройки")
async def settings_command(message: Message):
    if message.from_user.id not in user_preferences:
        await start_command(message)
        return 
    await message.answer(
        "Настройки:",
        reply_markup=get_settings_keyboard()
    )

@router.message(F.text == "📷 Описать фото")
async def enable_photo_description(message: Message):
    photo_description_mode[message.from_user.id] = True
    await message.answer(
        "Отправьте фото для описания:",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "🤖 Выбрать голос бота")
async def voice_choice(message: Message):
    await message.answer(
        "Выберите голос бота:",
        reply_markup=get_voice_keyboard()
    )

@router.message(F.text == "↩️ Назад")
async def back_command(message: Message):
    await message.answer(
        "Главная:",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "🎧 Всегда отвечать голосом")
async def set_voice_response(message: Message):
    if message.from_user.id not in user_preferences:
        user_preferences[message.from_user.id] = {}
    
    user_preferences[message.from_user.id]["output"] = "voice"
    await message.answer("Буду отвечать голосом.", reply_markup=get_main_keyboard())

@router.message(F.text == "📄 Всегда отвечать текстом")
async def set_text_response(message: Message):
    if message.from_user.id not in user_preferences:
        user_preferences[message.from_user.id] = {}
    
    user_preferences[message.from_user.id]["output"] = "text"
    await message.answer("Буду отвечать текстом.", reply_markup=get_main_keyboard())

@router.message(F.text == "Ахмед")
async def set_ahmad_voice(message: Message):
    if message.from_user.id not in user_preferences:
        user_preferences[message.from_user.id] = {}
    
    user_preferences[message.from_user.id]["voice"] = "Ahmad-PlayAI"
    await message.answer("Буду отвечать голосом Ахмеда.", reply_markup=get_main_keyboard())

@router.message(F.text == "Кхалид")
async def set_khalid_voice(message: Message):
    if message.from_user.id not in user_preferences:
        user_preferences[message.from_user.id] = {}
    
    user_preferences[message.from_user.id]["voice"] = "Khalid-PlayAI"
    await message.answer("Буду отвечать голосом Кхалида.", reply_markup=get_main_keyboard())

@router.message(F.text == "Амира")
async def set_amira_voice(message: Message):
    if message.from_user.id not in user_preferences:
        user_preferences[message.from_user.id] = {}
    
    user_preferences[message.from_user.id]["voice"] = "Amira-PlayAI"
    await message.answer("Буду отвечать голосом Амиры.", reply_markup=get_main_keyboard())

@router.message()
async def handle_messages(message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_preferences:
        await start_command(message)
        return
    if photo_description_mode.get(user_id, False):
        photo_description_mode[user_id] = False
    
        try:
            file_id = message.photo[-1].file_id
            file = await bot.get_file(file_id)
            file_path = file.file_path
            
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                await bot.download_file(file_path, tmp_file.name)
                tmp_path = tmp_file.name
            
            description = get_image_description(tmp_path)
            
            await message.answer(
                f"📸 Описание фото:\n{description}",
                reply_markup=get_main_keyboard()
            )
            
        except Exception as e:
            logging.error(f"Ошибка обработки фото: {str(e)}")
            await message.answer(
                "⚠️ Не удалось обработать фото. Попробуйте другое изображение.",
                reply_markup=get_main_keyboard()
            )
            
        finally:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
    if image_generation_mode.get(user_id, False):
        image_generation_mode[message.from_user.id] = False
    
        processing_msg = await message.answer("🖌️ Генерация изображения... это может занять некоторое время")
        
        try:
            result = generate_image(message.text)
            
            if not result:
                await message.answer("Не удалось сгенерировать изображение. Попробуйте другой запрос.")
                return

            if result["type"] == "url":
                async with aiohttp.ClientSession() as session:
                    async with session.get(result["content"]) as response:
                        if response.status == 200:
                            img_data = await response.read()
                            
                            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                                tmp_file.write(img_data)
                                tmp_path = tmp_file.name
                            
                            await message.answer_photo(
                                FSInputFile(tmp_path),
                                caption="Ваше изображение готово!",
                                reply_markup=get_main_keyboard()
                            )
                            
                            os.unlink(tmp_path)
                        else:
                            raise ValueError(f"HTTP error {response.status}")

            elif result["type"] == "file":
                await message.answer_photo(
                    FSInputFile(result["content"]),
                    caption="Ваше изображение готово!",
                    reply_markup=get_main_keyboard()
                )
                
        except Exception as e:
            logging.error(f"Image processing error: {str(e)}", exc_info=True)
            await message.answer("⚠️ Произошла ошибка при обработке изображения")
            
        finally:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
            except:
                pass
        return
    
    if message.text in ["⚙️ Настройки", "↩️ Назад", "🎧 Всегда отвечать голосом", 
                       "📄 Всегда отвечать текстом", "🤖 Выбрать голос бота",
                       "Ахмед", "Кхалид", "Амира", "🎨 Сгенерировать изображение"]:
        return
    
    preferences = user_preferences[user_id]
    response_type = preferences.get("output", "text")
    voice_model = preferences.get("voice", "Ahmad-PlayAI")

    if message.voice:
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        await bot.download_file(file_path, "message.wav")
        trans = transcribe_audio("message.wav")
        response_text = ask(trans)
    elif message.text:
        response_text = ask(message.text)
    else:
        return

    if response_type == "voice":
        audio_file = text_to_speech1(response_text, "response.ogg", voice_model)
        if audio_file:
            voice = FSInputFile(audio_file)
            await message.answer_voice(voice, reply_markup=get_main_keyboard())
            os.remove(audio_file)
        else:
            await message.answer(response_text, reply_markup=get_main_keyboard())
    else:
        await message.answer(response_text, reply_markup=get_main_keyboard())

dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())