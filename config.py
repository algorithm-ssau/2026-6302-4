# config.py
# Конфигурация новостного агента NewsAgent

import os
from dotenv import load_dotenv

load_dotenv()

# КЛЮЧЕВЫЕ СЛОВА
KEYWORDS = [
    # Технологии
    "технологии", "искусственный интеллект", "нейросети",
    "машинное обучение", "программирование", "стартапы",
    "инновации", "IT", "цифровизация", "автоматизация",
    "гаджеты", "роботы", "приложения", "софт", "hardware",

    # Наука
    "наука", "исследование", "ученые", "открытие", "эксперимент",
    "космос", "физика", "химия", "биология", "генетика",
    "медицина", "вакцина", "лекарство",

    # Бизнес и экономика
    "экономика", "бизнес", "финансы", "инвестиции", "акции",
    "биржа", "банк", "валюта", "рынок", "компания", "корпорация",

    # Общие новостные слова
    "россия", "москва", "президент", "правительство", "закон",
    "новый", "запуск", "релиз", "обновление", "проект",
    "разработка", "создание", "строительство",

    # Спорт
    "спорт", "футбол", "хоккей", "чемпионат", "турнир", "матч",

    # Культура
    "культура", "кино", "музыка", "выставка", "фестиваль",
    "концерт", "премьера",

    # Происшествия и события
    "событие", "происшествие", "катастрофа", "рекорд",
    "достижение", "результат", "показатель",

    # Политика
    "политика", "выборы", "саммит", "переговоры", "соглашение",
    "договор", "санкции", "сотрудничество",
]

# Стоп-слова для фильтрации спама
STOP_WORDS = [
    "реклама",
    "акция",
    "распродажа",
    "вакансия",
    "требуется",
    "курсы",
    "вебинар",
    "ставки",
    "казино",
]

# ИСТОЧНИКИ
RSS_SOURCES = [
    "https://lenta.ru/rss/news",
    "https://habr.com/ru/rss/all/",
    "https://ria.ru/export/rss2/index.xml",
    "https://www.rbc.ru/news/rss/news",
    "https://vc.ru/rss",
]

HTML_SOURCES = [
    "https://lenta.ru",
    "https://ria.ru",
    "https://www.rbc.ru",
    "https://habr.com/ru/all/",
]

# ЛИМИТЫ
MAX_NEWS_PER_CYCLE = 10
MAX_NEWS_PER_SOURCE = 5
MAX_NEWS_PER_DAY_PER_USER = 20
REQUEST_TIMEOUT = 5
CHECK_INTERVAL = 3600

# ФИЛЬТРАЦИЯ
CONTEXT_THRESHOLD = 0.1  # Понижен с 0.3 до 0.1 для лучшего захвата
USE_SENT_CACHE = True

# СТИЛИ
DEFAULT_STYLE = "formal"
STYLES = {
    "brief": {
        "description": "Кратко, только самое важное",
        "max_length": 200,
        "tone": "нейтральный",
        "include_time": False,
        "include_source": True,
        "emoji": False
    },
    "detailed": {
        "description": "Подробное изложение с деталями",
        "max_length": 2000,
        "tone": "аналитический",
        "include_time": True,
        "include_source": True,
        "emoji": False
    }
}

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
TIMEZONE = "Europe/Moscow"
ACTIVE_DAYS = [0, 1, 2, 3, 4]

LOG_LEVEL = "INFO"
LOG_FILE = "newsagent.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

TOPIC_DESCRIPTION = "новости про технологии, искусственный интеллект и программирование"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
MAX_WORKERS = 5
DATABASE_URL = "sqlite:///newsagent.db"

# Стиль по умолчанию для пересказа
DEFAULT_SUMMARY_STYLE = "detailed"