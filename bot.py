import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from utils.config import BOT_TOKEN
from utils.speech_to_text import transcribe_audio
from utils.chatgpt_api import ask
from utils.text_to_speech import text_to_speech1
import os

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

user_preferences = {}

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Настройки")]
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

@router.message(CommandStart())
async def start_command(message: Message):
    user_preferences[message.from_user.id] = {
        "output": "text", 
        "voice": "Ahmad-PlayAI"  
    }
    await message.answer(
        "Привет! Я бот, который может отвечать текстом или голосом.\n"
        "Выбери формат ответа:",
        reply_markup=get_main_keyboard()
    )

@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
async def settings_command(message: Message):
    if message.from_user.id not in user_preferences:
        await start_command(message)
        return
    
    await message.answer(
        "Настройки:",
        reply_markup=get_settings_keyboard()
    )

@router.message(F.text == "📄 Всегда отвечать текстом")
async def set_text_response(message: Message):
    if message.from_user.id not in user_preferences:
        user_preferences[message.from_user.id] = {}
    
    user_preferences[message.from_user.id]["output"] = "text"
    await message.answer("Буду отвечать текстом.", reply_markup=get_main_keyboard())

@router.message(F.text == "🎧 Всегда отвечать голосом")
async def set_voice_response(message: Message):
    if message.from_user.id not in user_preferences:
        user_preferences[message.from_user.id] = {}
    
    user_preferences[message.from_user.id]["output"] = "voice"
    await message.answer("Буду отвечать голосом.", reply_markup=get_main_keyboard())

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
    
    if message.text in ["⚙️ Настройки", "↩️ Назад", "🎧 Всегда отвечать голосом", 
                       "📄 Всегда отвечать текстом", "🤖 Выбрать голос бота",
                       "Ахмед", "Кхалид", "Амира"]:
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

    if response_type == "voice":
        audio_file = text_to_speech1(
            response_text, 
            "response.ogg",
            voice_model
        )
        if audio_file:
            voice = FSInputFile(audio_file)
            await message.answer_voice(voice, reply_markup=get_main_keyboard())
            os.remove(audio_file)
        else:
            await message.answer(response_text, reply_markup=get_main_keyboard())
    elif response_type == "text":
        await message.answer(response_text, reply_markup=get_main_keyboard())

dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())