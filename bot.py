import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from utils.config import BOT_TOKEN
from utils.speech_to_text import transcribe_audio


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
        await message.answer(trans)
    else:
        await message.answer(f"Вы отправили: {message.text}")


dp.include_router(router)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
