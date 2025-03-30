import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile
from utils.config import BOT_TOKEN
from utils.speech_to_text import transcribe_audio
from utils.chatgpt_api import ask
from utils.text_to_speech import text_to_speech1
import os


logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()


@router.message(CommandStart())
async def start_command(message: Message):
    await message.answer("Привет! Отправь мне текстовое или голосовое сообщение.")


@router.message()
async def message_handlers(message: Message):
    if message.voice:
        voice = message.audio
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        await bot.download_file(file_path, "message.wav")
        trans = transcribe_audio("message.wav")
        response_text = ask(trans)
        audio_file = text_to_speech1(response_text, "response.ogg")
        if audio_file:
            voice = FSInputFile(audio_file)
            await message.answer_voice(voice)
            os.remove(audio_file)
        else:
            await message.answer(response_text)
    else:
        
        await message.answer(ask(message.text))


dp.include_router(router)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
