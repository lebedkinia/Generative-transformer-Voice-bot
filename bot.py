import asyncio
import logging
import aiohttp
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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
from datetime import datetime

logging.basicConfig(level=logging.INFO)
load_dotenv()


def init_db():
    conn = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        model TEXT,
        rating INTEGER,
        comment TEXT,
        created_at TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        suggestion TEXT,
        created_at TEXT
    )
    ''')
    conn.commit()
    conn.close()


init_db()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()
router = Router()


class FeedbackStates(StatesGroup):
    choosing_model = State()
    rating = State()
    comment = State()


class SuggestionStates(StatesGroup):
    waiting_for_suggestion = State()


# Хранилище пользовательских настроек
user_preferences = {}
image_generation_mode = {}
photo_description_mode = {}
feedback_mode = {}
suggestion_mode = {}


def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💬 Чат бот с ИИ"),
                KeyboardButton(text="⚙️ Настройки чата")
            ],
            [KeyboardButton(text="🎨 Сгенерировать изображение")],
            [
                KeyboardButton(text="📷 Описать фото"),
                KeyboardButton(text="⚙️ Настройки фото")
            ],
            [
                KeyboardButton(text="💬 Оставить отзыв"),
                KeyboardButton(text="💡 Предложить улучшение")
            ]
        ],
        resize_keyboard=True,
        persistent=True
    )


def get_chat_settings_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎧 Отвечать голосом (чат)")],
            [KeyboardButton(text="📄 Отвечать текстом (чат)")],
            [KeyboardButton(text="🤖 Выбрать голос (чат)")],
            [KeyboardButton(text="↩️ Назад")]
        ],
        resize_keyboard=True,
        persistent=True
    )


def get_photo_settings_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎧 Отвечать голосом (фото)")],
            [KeyboardButton(text="📄 Отвечать текстом (фото)")],
            [KeyboardButton(text="🗣️ Выбрать голос (фото)")],
            [KeyboardButton(text="↩️ Назад")]
        ],
        resize_keyboard=True,
        persistent=True
    )


def get_chat_voice_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Ахмед (чат)")],
            [KeyboardButton(text="Кхалид (чат)")],
            [KeyboardButton(text="Амира (чат)")],
            [KeyboardButton(text="↩️ Назад")]
        ],
        resize_keyboard=True,
        persistent=True
    )


def get_photo_voice_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Ахмед (фото)")],
            [KeyboardButton(text="Кхалид (фото)")],
            [KeyboardButton(text="Амира (фото)")],
            [KeyboardButton(text="↩️ Назад")]
        ],
        resize_keyboard=True,
        persistent=True
    )


def get_models_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ChatGPT")],
            [KeyboardButton(text="Генерация изображений")],
            [KeyboardButton(text="Описание изображений")],
            [KeyboardButton(text="Текст в речь")],
            [KeyboardButton(text="↩️ Назад")]
        ],
        resize_keyboard=True,
        persistent=True
    )


def get_rating_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="1 ⭐"),
                KeyboardButton(text="2 ⭐⭐")
            ],
            [
                KeyboardButton(text="3 ⭐⭐⭐"),
                KeyboardButton(text="4 ⭐⭐⭐⭐")
            ],
            [
                KeyboardButton(text="5 ⭐⭐⭐⭐⭐")
            ],
            [KeyboardButton(text="↩️ Назад")]
        ],
        resize_keyboard=True,
        persistent=True
    )


async def save_feedback(user_id: int, username: str, model: str, rating: int, comment: str):
    conn = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO feedbacks (user_id, username, model, rating, comment, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, username, model, rating, comment, datetime.now().isoformat()))
    conn.commit()
    conn.close()


async def save_suggestion(user_id: int, username: str, suggestion: str):
    conn = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO suggestions (user_id, username, suggestion, created_at)
    VALUES (?, ?, ?, ?)
    ''', (user_id, username or f"user_{user_id}", suggestion, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def init_user_preferences(user_id: int):
    if user_id not in user_preferences:
        user_preferences[user_id] = {
            "chat_output": "text",
            "chat_voice": "Ahmad-PlayAI",
            "photo_output": "text",
            "photo_voice": "Ahmad-PlayAI"
        }


@router.message(CommandStart())
async def start_command(message: Message):
    init_user_preferences(message.from_user.id)
    image_generation_mode[message.from_user.id] = False
    photo_description_mode[message.from_user.id] = False
    feedback_mode[message.from_user.id] = False
    suggestion_mode[message.from_user.id] = False
    await message.answer(
        "🌟 Добро пожаловать в многофункционального ИИ-бота! 🌟\n\n"
        "Я умею:\n"
        "💬 Общаться как ChatGPT (текст/голос)\n"
        "🎨 Создавать уникальные изображения по вашему описанию\n"
        "📷 Анализировать и описывать фотографии\n\n"
        "Выберите действие на клавиатуре ниже:\n\n\n"
        "💬 Режим чат-бота активирован!\n\n"
        "Вы можете:\n"
        "✏️ Написать текстовое сообщение\n"
        "🎤 Или отправить голосовое сообщение\n\n"
        "Я постараюсь дать максимально полезный и развернутый ответ!",
        reply_markup=get_main_keyboard()
    )


@router.message(SuggestionStates.waiting_for_suggestion, F.text == "↩️ Отменить")
async def cancel_suggestion(message: Message, state: FSMContext):
    await state.clear()
    suggestion_mode[message.from_user.id] = False
    await message.answer(
        "Отправка предложения отменена.",
        reply_markup=get_main_keyboard()
    )


@router.message(SuggestionStates.waiting_for_suggestion)
async def process_suggestion(message: Message, state: FSMContext):
    suggestion = message.text
    await save_suggestion(
        user_id=message.from_user.id,
        username=message.from_user.username,
        suggestion=suggestion
    )

    await message.answer(
        "Спасибо за ваше предложение! Мы обязательно рассмотрим его для улучшения бота.",
        reply_markup=get_main_keyboard()
    )
    await state.clear()
    suggestion_mode[message.from_user.id] = False


@router.message(FeedbackStates.choosing_model, F.text.in_(["ChatGPT", "Генерация изображений", "Описание изображений", "Текст в речь"]))
async def choose_model(message: Message, state: FSMContext):
    await state.update_data(model=message.text)
    await state.set_state(FeedbackStates.rating)
    await message.answer(
        "Пожалуйста, оцените функционал от 1 до 5 звезд:",
        reply_markup=get_rating_keyboard()
    )


@router.message(FeedbackStates.rating, F.text.regexp(r'^\d ⭐+$'))
async def set_rating(message: Message, state: FSMContext):
    rating = int(message.text.split()[0])
    await state.update_data(rating=rating)
    await state.set_state(FeedbackStates.comment)
    await message.answer(
        "Напишите ваш отзыв или комментарий:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Пропустить")]],
            resize_keyboard=True
        )
    )


@router.message(FeedbackStates.comment)
async def set_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    model = data.get('model', 'Неизвестно')
    rating = data.get('rating', 0)
    comment = message.text if message.text != "Пропустить" else "Без комментария"

    await save_feedback(
        user_id=message.from_user.id,
        username=message.from_user.username or f"user_{message.from_user.id}",
        model=model,
        rating=rating,
        comment=comment
    )

    await message.answer(
        f"Спасибо за ваш отзыв о {model}!\n"
        f"Оценка: {rating} звезд\n"
        f"Комментарий: {comment}",
        reply_markup=get_main_keyboard()
    )
    await state.clear()


@router.message(F.text == "⚙️ Настройки чата")
async def chat_settings_command(message: Message):
    init_user_preferences(message.from_user.id)
    await message.answer(
        "⚙️ Настройки чат-бота:\n\n"
        "Здесь вы можете настроить:\n"
        "🔉 Формат ответов (текст/голос)\n"
        "🗣️ Голос бота (если выбран голосовой ответ)\n\n"
        "Выберите параметр для изменения:",
        reply_markup=get_chat_settings_keyboard()
    )


@router.message(F.text == "⚙️ Настройки фото")
async def photo_settings_command(message: Message):
    init_user_preferences(message.from_user.id)
    await message.answer(
        "⚙️ Настройки описания фото:\n\n"
        "Здесь вы можете настроить:\n"
        "🔉 Формат ответов (текст/голос)\n"
        "🗣️ Голос бота (если выбран голосовой ответ)\n\n"
        "Выберите параметр для изменения:",
        reply_markup=get_photo_settings_keyboard()
    )


@router.message(F.text == "💬 Оставить отзыв")
async def start_feedback(message: Message, state: FSMContext):
    await state.set_state(FeedbackStates.choosing_model)
    await message.answer(
        "📝 Мы ценим ваше мнение!\n\n"
        "Пожалуйста, выберите функционал, о котором хотите оставить отзыв:",
        reply_markup=get_models_keyboard()
    )


@router.message(F.text == "💡 Предложить улучшение")
async def start_suggestion(message: Message, state: FSMContext):
    await state.set_state(SuggestionStates.waiting_for_suggestion)
    await message.answer(
        "💡 Ваши идеи делают нас лучше!\n\n"
        "Пожалуйста, напишите ваше предложение по улучшению бота.\n"
        "Мы внимательно изучим каждое сообщение!",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="↩️ Отменить")]],
            resize_keyboard=True
        )
    )


@router.message(F.text == "🤖 Выбрать голос (чат)")
async def chat_voice_choice(message: Message):
    init_user_preferences(message.from_user.id)
    await message.answer(
        "Выберите голос для чат-бота:",
        reply_markup=get_chat_voice_keyboard()
    )


@router.message(F.text == "🗣️ Выбрать голос (фото)")
async def photo_voice_choice(message: Message):
    init_user_preferences(message.from_user.id)
    await message.answer(
        "Выберите голос для описания фото:",
        reply_markup=get_photo_voice_keyboard()
    )


@router.message(F.text == "↩️ Назад")
async def back_command(message: Message):
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_keyboard()
    )


@router.message(F.text == "🎧 Отвечать голосом (чат)")
async def set_chat_voice_response(message: Message):
    init_user_preferences(message.from_user.id)
    user_preferences[message.from_user.id]["chat_output"] = "voice"
    await message.answer("В чате буду отвечать голосом.", reply_markup=get_main_keyboard())


@router.message(F.text == "📄 Отвечать текстом (чат)")
async def set_chat_text_response(message: Message):
    init_user_preferences(message.from_user.id)
    user_preferences[message.from_user.id]["chat_output"] = "text"
    await message.answer("В чате буду отвечать текстом.", reply_markup=get_main_keyboard())


@router.message(F.text == "Ахмед (чат)")
async def set_chat_ahmad_voice(message: Message):
    init_user_preferences(message.from_user.id)
    user_preferences[message.from_user.id]["chat_voice"] = "Ahmad-PlayAI"
    await message.answer("В чате буду отвечать голосом Ахмеда.", reply_markup=get_main_keyboard())


@router.message(F.text == "Кхалид (чат)")
async def set_chat_khalid_voice(message: Message):
    init_user_preferences(message.from_user.id)
    user_preferences[message.from_user.id]["chat_voice"] = "Khalid-PlayAI"
    await message.answer("В чате буду отвечать голосом Кхалида.", reply_markup=get_main_keyboard())


@router.message(F.text == "Амира (чат)")
async def set_chat_amira_voice(message: Message):
    init_user_preferences(message.from_user.id)
    user_preferences[message.from_user.id]["chat_voice"] = "Amira-PlayAI"
    await message.answer("В чате буду отвечать голосом Амиры.", reply_markup=get_main_keyboard())


@router.message(F.text == "🎧 Отвечать голосом (фото)")
async def set_photo_voice_response(message: Message):
    init_user_preferences(message.from_user.id)
    user_preferences[message.from_user.id]["photo_output"] = "voice"
    await message.answer("Описание фото буду отправлять голосом.", reply_markup=get_main_keyboard())


@router.message(F.text == "📄 Отвечать текстом (фото)")
async def set_photo_text_response(message: Message):
    init_user_preferences(message.from_user.id)
    user_preferences[message.from_user.id]["photo_output"] = "text"
    await message.answer("Описание фото буду отправлять текстом.", reply_markup=get_main_keyboard())


@router.message(F.text == "Ахмед (фото)")
async def set_photo_ahmad_voice(message: Message):
    init_user_preferences(message.from_user.id)
    user_preferences[message.from_user.id]["photo_voice"] = "Ahmad-PlayAI"
    await message.answer("Описание фото буду отправлять голосом Ахмеда.", reply_markup=get_main_keyboard())


@router.message(F.text == "Кхалид (фото)")
async def set_photo_khalid_voice(message: Message):
    init_user_preferences(message.from_user.id)
    user_preferences[message.from_user.id]["photo_voice"] = "Khalid-PlayAI"
    await message.answer("Описание фото буду отправлять голосом Кхалида.", reply_markup=get_main_keyboard())


@router.message(F.text == "Амира (фото)")
async def set_photo_amira_voice(message: Message):
    init_user_preferences(message.from_user.id)
    user_preferences[message.from_user.id]["photo_voice"] = "Amira-PlayAI"
    await message.answer("Описание фото буду отправлять голосом Амиры.", reply_markup=get_main_keyboard())


async def handle_chat_mode(message: Message):
    user_id = message.from_user.id

    preferences = user_preferences.get(user_id, {
        "chat_output": "text",
        "chat_voice": "Ahmad-PlayAI"
    })

    if message.voice:
        try:
            processing_msg = await message.answer("🔊 Обрабатываю голосовое сообщение...")

            file_id = message.voice.file_id
            file = await bot.get_file(file_id)
            file_path = file.file_path

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                await bot.download_file(file_path, tmp_file.name)
                tmp_path = tmp_file.name

            user_text = transcribe_audio(tmp_path)
            os.unlink(tmp_path)

            await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)

            if not user_text:
                await message.answer("❌ Не удалось распознать голосовое сообщение. Попробуйте ещё раз.")
                return

            await message.answer(f"🎤 Вы сказали:\n\n{user_text}")

        except Exception as e:
            logging.error(f"Voice processing error: {str(e)}")
            await message.answer("❌ Произошла ошибка при обработке голосового сообщения")
            return

    elif message.text:
        user_text = message.text
    else:
        return

    try:
        thinking_msg = await message.answer("💭 Думаю над ответом...")
        response_text = ask(user_text)
        await bot.delete_message(chat_id=message.chat.id, message_id=thinking_msg.message_id)

        if not response_text:
            await message.answer("❌ Не удалось получить ответ. Попробуйте ещё раз.")
            return

    except Exception as e:
        logging.error(f"Chat error: {str(e)}")
        await message.answer("❌ Произошла ошибка при генерации ответа")
        return

    if preferences["chat_output"] == "voice":
        try:
            converting_msg = await message.answer("🔊 Преобразую ответ в голос...")

            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_file:
                audio_path = tmp_file.name

            success = text_to_speech1(
                response_text, audio_path, preferences["chat_voice"])

            if success:
                await message.answer_voice(
                    FSInputFile(audio_path),
                    caption="💬 Ответ на ваше сообщение:",
                    reply_markup=get_main_keyboard()
                )
            else:
                await message.answer(
                    f"💬 Ответ на ваше сообщение:\n\n{response_text}",
                    reply_markup=get_main_keyboard()
                )

            os.unlink(audio_path)
            await bot.delete_message(chat_id=message.chat.id, message_id=converting_msg.message_id)

        except Exception as e:
            logging.error(f"Voice generation error: {str(e)}")
            await message.answer(
                f"💬 Ответ на ваше сообщение:\n\n{response_text}",
                reply_markup=get_main_keyboard()
            )

    else:
        await message.answer(
            f"💬 Ответ на ваше сообщение:\n\n{response_text}",
            reply_markup=get_main_keyboard()
        )


@router.message()
async def handle_messages(message: Message):
    user_id = message.from_user.id

    if user_id not in user_preferences:
        await start_command(message)
        return

    def reset_all_modes():
        nonlocal user_id
        image_generation_mode[user_id] = False
        photo_description_mode[user_id] = False
        feedback_mode[user_id] = False
        suggestion_mode[user_id] = False

    if message.text == "💬 Чат бот с ИИ":
        reset_all_modes()
        await message.answer(
            "💬 Режим чат-бота активирован!\n\n"
            "Вы можете:\n"
            "✏️ Написать текстовое сообщение\n"
            "🎤 Или отправить голосовое сообщение\n\n"
            "Я постараюсь дать максимально полезный и развернутый ответ!",
            reply_markup=get_main_keyboard()
        )
        return

    elif message.text == "🎨 Сгенерировать изображение":
        reset_all_modes()
        image_generation_mode[user_id] = True
        await message.answer(
            "🎨 Режим генерации изображений активирован!\n\n"
            "Отправьте мне текстовое описание того, что вы хотите увидеть, "
            "или голосовое сообщение с вашим запросом.\n\n"
            "Например:\n"
            "«Космический корабль в стиле ретро-футуризм»\n"
            "«Реалистичный портрет кота в шляпе»\n\n"
            "Я создам для вас уникальное изображение!",
            reply_markup=get_main_keyboard()
        )
        return

    elif message.text == "📷 Описать фото":
        reset_all_modes()
        photo_description_mode[user_id] = True
        await message.answer(
            "📷 Режим анализа фотографий активирован!\n\n"
            "Просто отправьте мне фотографию, и я:\n"
            "🔍 Подробно опишу что на ней изображено\n"
            "🎨 Определю стиль и композицию\n"
            "💡 Дам интересные заметки о содержимом\n\n"
            "Отправьте одно фото для анализа:",
            reply_markup=get_main_keyboard()
        )
        return

    elif message.text == "💬 Оставить отзыв":
        reset_all_modes()
        await start_feedback(message, FSMContext)
        return

    elif message.text == "💡 Предложить улучшение":
        reset_all_modes()
        suggestion_mode[user_id] = True
        await start_suggestion(message, FSMContext)
        return

    if not any([
        image_generation_mode.get(user_id, False),
        photo_description_mode.get(user_id, False),
        feedback_mode.get(user_id, False),
        suggestion_mode.get(user_id, False)
    ]):
        await handle_chat_mode(message)
        return

    if suggestion_mode.get(user_id, False):
        suggestion = message.text
        await save_suggestion(
            user_id=user_id,
            username=message.from_user.username,
            suggestion=suggestion
        )
        await message.answer(
            "💌 Спасибо за ваше предложение! Мы обязательно рассмотрим его для улучшения бота.",
            reply_markup=get_main_keyboard()
        )
        return

    if photo_description_mode.get(user_id, False):
        try:
            if not message.photo:
                await message.answer(
                    "📷 Пожалуйста, отправьте именно фото для описания.",
                    reply_markup=get_main_keyboard()
                )
                return

            file_id = message.photo[-1].file_id
            file = await bot.get_file(file_id)
            file_path = file.file_path

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                await bot.download_file(file_path, tmp_file.name)
                tmp_path = tmp_file.name
            description = get_image_description(tmp_path)

            output_type = user_preferences[user_id].get("photo_output", "text")
            voice_model = user_preferences[user_id].get(
                "photo_voice", "Ahmad-PlayAI")

            if output_type == "voice":
                audio_file = text_to_speech1(
                    description, "photo_description.ogg", voice_model)
                if audio_file:
                    voice = FSInputFile(audio_file)
                    await message.answer_voice(
                        voice,
                        caption="🔍 Вот описание вашего фото:",
                        reply_markup=get_main_keyboard()
                    )
                    os.remove(audio_file)
                else:
                    await message.answer(
                        f"🔍 Описание фото:\n\n{description}",
                        reply_markup=get_main_keyboard()
                    )
            else:
                await message.answer(
                    f"🔍 Описание фото:\n\n{description}",
                    reply_markup=get_main_keyboard()
                )

        except Exception as e:
            logging.error(f"Ошибка обработки фото: {str(e)}")
            await message.answer(
                "⚠️ К сожалению, не удалось обработать фото. Попробуйте другое изображение.",
                reply_markup=get_main_keyboard()
            )

        finally:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        return

    if image_generation_mode.get(user_id, False):
        processing_msg = await message.answer("🎨 Генерация изображения... Это может занять до минуты")

        try:
            if message.voice:
                file_id = message.voice.file_id
                file = await bot.get_file(file_id)
                file_path = file.file_path
                await bot.download_file(file_path, "voice_prompt.wav")
                prompt = transcribe_audio("voice_prompt.wav")
                os.remove("voice_prompt.wav")
                await message.answer(f"🎤 Распознанный запрос: {prompt}")
            else:
                prompt = message.text

            result = generate_image(prompt)

            if not result:
                await message.answer(
                    "⚠️ Не удалось сгенерировать изображение. Попробуйте другой запрос.",
                    reply_markup=get_main_keyboard()
                )
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
                                caption="🖼️ Ваше изображение готово!",
                                reply_markup=get_main_keyboard()
                            )
                            os.unlink(tmp_path)
                        else:
                            raise ValueError(f"HTTP error {response.status}")

            elif result["type"] == "file":
                await message.answer_photo(
                    FSInputFile(result["content"]),
                    caption="🖼️ Ваше изображение готово!",
                    reply_markup=get_main_keyboard()
                )

        except Exception as e:
            logging.error(f"Image generation error: {str(e)}", exc_info=True)
            await message.answer(
                "⚠️ Произошла ошибка при генерации изображения. Попробуйте позже.",
                reply_markup=get_main_keyboard()
            )

        finally:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
            except:
                pass
        return


dp.include_router(router)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
