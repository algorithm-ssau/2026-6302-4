# config.py
# Конфигурация новостного агента NewsAgent

# КЛЮЧЕВЫЕ СЛОВА
KEYWORDS = [
    "технологии",
    "искусственный интеллект",
    "нейросети",
    "машинное обучение",
    "программирование",
    "стартапы",
    "инновации",
    "IT",
    "цифровизация",
    "автоматизация",
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
]

#ИСТОЧНИКИ
# Для RSSparser.py - get_news_from_multiple_rss()
RSS_SOURCES = [
    "https://lenta.ru/rss/news",
    "https://habr.com/ru/rss/all/",
    "https://ria.ru/export/rss2/index.xml",
    "https://www.rbc.ru/news/rss/news",
    "https://vc.ru/rss",
]

# Для HTMLparser.py - parse_html_page()
HTML_SOURCES = [
    "https://lenta.ru",
    "https://ria.ru",
    "https://www.rbc.ru",
    "https://habr.com/ru/all/",
]

#  ЛИМИТЫ
# Максимум новостей за один цикл парсинга
MAX_NEWS_PER_CYCLE = 10

# Максимум новостей с одного источника
MAX_NEWS_PER_SOURCE = 5

# Максимум новостей в день для одного пользователя
MAX_NEWS_PER_DAY_PER_USER = 20

# Timeout для запросов (секунды)
REQUEST_TIMEOUT = 5

# Интервал проверки новостей (секунды)
CHECK_INTERVAL = 3600  # 1 час

#  ФИЛЬТРАЦИЯ
# Порог для filter_by_context() (0-1)
CONTEXT_THRESHOLD = 0.3

# Включить ли кэш отправленных новостей (filter_already_sent)
USE_SENT_CACHE = True

# СТИЛИ ИЗЛОЖЕНИЯ
# Стиль по умолчанию
DEFAULT_STYLE = "formal"

# Доступные стили для пользователя
STYLES = {
    "formal": {
        "description": "Официальный деловой стиль",
        "max_length": 500,
        "tone": "профессиональный",
        "include_time": True,
        "include_source": True,
        "emoji": False
    },
    "casual": {
        "description": "Неформальный разговорный стиль",
        "max_length": 400,
        "tone": "дружелюбный",
        "include_time": True,
        "include_source": True,
        "emoji": True
    },
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
        "max_length": 800,
        "tone": "аналитический",
        "include_time": True,
        "include_source": True,
        "emoji": False
    }
}

# ID администратора для уведомлений
ADMIN_ID = 0

# РАСПИСАНИЕ
# Часовой пояс
TIMEZONE = "Europe/Moscow"

# Дни недели (0=понедельник, 6=воскресенье)
ACTIVE_DAYS = [0, 1, 2, 3, 4]  # рабочие дни

# ЛОГИРОВАНИЕ
LOG_LEVEL = "INFO"
LOG_FILE = "newsagent.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ДОПОЛНИТЕЛЬНО
# User-Agent для запросов
USER_AGENT = "Mozilla/5.0"

# Количество потоков для параллельного парсинга
MAX_WORKERS = 5

# База данных для кэша
DATABASE_URL = "sqlite:///newsagent.db"