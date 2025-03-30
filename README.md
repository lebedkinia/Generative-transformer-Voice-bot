### Установка
Вы можете использовать `git clone https://github.com/lebedkinia/Generative-transformer-Voice-bot.git` или скачать и распаковать zip архив

### Для установки зависимостей используйте 
`pip install -r requirements.txt`

### Использование API ключей
Для работы кода необходимы api ключи:
- Создайте файл `config.py` в папке utils 
- В нем создайте константу `BOT_TOKEN`, в нее поместите ключ телеграм бота
- Создайте `GROQ_API_KEY`, туда поместите api ключ groq

После этого нужно перейти в корневую директорию проекта и запустить `bot.py` 
Команды для этого:
- `python bot.py`
- или `python3 bot.py`
