"""
VK-бот NewsAgent
Отправляет новости пользователям по подписке
"""
import sys
import os
import threading
import time
import sqlite3
from datetime import datetime

# Добавляем текущую папку в пути поиска модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

from config import CHECK_INTERVAL, DEFAULT_STYLE, STYLES
from agent import run_agent


# ========== НАСТРОЙКИ - ВСТАВЬТЕ ВАШИ ДАННЫЕ ==========
VK_TOKEN = "vk1.a.i1dQB0_Krcc7f0X8lO8kfB9N2H4tr4_l7nmlECeYLL1dCjHJslhP0mGVmnW3K63BmNpQWeuXhjmxWIw7IhsaszBPpf_v0J3lU-yFQHPSyvJEWtF42bsq1YD0jVWVFWPJhQgff2BI_9smMQfA4dpXquS3uBnSQqm8t-rso9Fy1DflKRUXkzoGBOQJVgj3Pxav0O9lifwDM-mfvczOUiDtyQ"  # Замените на ваш реальный токен
GROUP_ID = 237717966  # ID вашей группы


# ========== БАЗА ДАННЫХ ==========
def init_db():
    """Создаёт таблицы для хранения подписок пользователей"""
    conn = sqlite3.connect('newsagent.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            topic TEXT DEFAULT 'technology',
            style TEXT DEFAULT 'formal',
            is_active INTEGER DEFAULT 1,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id TEXT UNIQUE,
            user_id INTEGER,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


# ========== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ==========
def register_user(user_id: int, topic: str = "technology", style: str = "formal"):
    """Регистрирует пользователя в базе"""
    conn = sqlite3.connect('newsagent.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, topic, style, is_active)
        VALUES (?, ?, ?, 1)
    ''', (user_id, topic, style))

    conn.commit()
    conn.close()


def get_user_settings(user_id: int):
    """Получает настройки пользователя"""
    conn = sqlite3.connect('newsagent.db')
    cursor = conn.cursor()

    cursor.execute('SELECT topic, style FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    conn.close()

    if result:
        return {"topic": result[0], "style": result[1]}
    return None


def update_user_style(user_id: int, style: str):
    """Обновляет стиль пользователя"""
    if style not in STYLES:
        return False

    conn = sqlite3.connect('newsagent.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET style = ? WHERE user_id = ?', (style, user_id))
    conn.commit()
    conn.close()
    return True


def update_user_topic(user_id: int, topic: str):
    """Обновляет тему пользователя"""
    topics = ["technology", "sport", "business", "science", "it"]

    if topic not in topics:
        return False

    conn = sqlite3.connect('newsagent.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET topic = ? WHERE user_id = ?', (topic, user_id))
    conn.commit()
    conn.close()
    return True


def get_all_active_users():
    """Возвращает всех активных пользователей"""
    conn = sqlite3.connect('newsagent.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, topic, style FROM users WHERE is_active = 1')
    users = cursor.fetchall()
    conn.close()
    return users


# ========== ОТПРАВКА НОВОСТЕЙ ==========
def send_news_to_user(vk, user_id: int, topic: str, style: str):
    """Генерирует и отправляет новости конкретному пользователю"""
    try:
        # Генерируем подборку
        news_text = run_agent(
            style=style,
            for_telegram=False,
            limit_per_source=3
        )

        # Ограничиваем длину сообщения (VK лимит 4096 символов)
        if len(news_text) > 4000:
            news_text = news_text[:4000] + "\n\n... (обрезано)"

        # Отправляем пользователю
        vk.messages.send(
            user_id=user_id,
            message=news_text,
            random_id=0
        )

        print(f"[OK] Новости отправлены пользователю {user_id} (тема: {topic}, стиль: {style})")

    except Exception as e:
        print(f"[ERROR] Ошибка при отправке пользователю {user_id}: {e}")


def send_news_to_all():
    """Отправляет новости всем активным пользователям"""
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()

    users = get_all_active_users()
    print(f"[INFO] Отправка новостей {len(users)} пользователям...")

    for user_id, topic, style in users:
        send_news_to_user(vk, user_id, topic, style)


# ========== ОБРАБОТЧИК СООБЩЕНИЙ ==========
def create_main_keyboard():
    """Создаёт главную клавиатуру"""
    return {
        "one_time": False,
        "buttons": [
            [
                {"color": "primary", "action": {"type": "text", "label": "📰 Новости"}},
                {"color": "secondary", "action": {"type": "text", "label": "⚙ Настройки"}},
                {"color": "secondary", "action": {"type": "text", "label": "ℹ Помощь"}}
            ]
        ]
    }


def create_settings_keyboard():
    """Создаёт клавиатуру настроек"""
    return {
        "one_time": True,
        "buttons": [
            [
                {"color": "primary", "action": {"type": "text", "label": "📂 Тема"}},
                {"color": "primary", "action": {"type": "text", "label": "🎨 Стиль"}}
            ],
            [
                {"color": "secondary", "action": {"type": "text", "label": "◀ Назад"}}
            ]
        ]
    }


def create_topics_keyboard():
    """Создаёт клавиатуру выбора темы"""
    return {
        "one_time": True,
        "buttons": [
            [
                {"color": "primary", "action": {"type": "text", "label": "💻 Технологии"}},
                {"color": "primary", "action": {"type": "text", "label": "⚽ Спорт"}}
            ],
            [
                {"color": "primary", "action": {"type": "text", "label": "📊 Бизнес"}},
                {"color": "primary", "action": {"type": "text", "label": "🔬 Наука"}}
            ],
            [
                {"color": "primary", "action": {"type": "text", "label": "💻 IT"}},
                {"color": "secondary", "action": {"type": "text", "label": "◀ Назад"}}
            ]
        ]
    }


def create_styles_keyboard():
    """Создаёт клавиатуру выбора стиля"""
    return {
        "one_time": True,
        "buttons": [
            [
                {"color": "primary", "action": {"type": "text", "label": "📋 Официальный"}},
                {"color": "primary", "action": {"type": "text", "label": "💬 Неформальный"}}
            ],
            [
                {"color": "primary", "action": {"type": "text", "label": "📝 Краткий"}},
                {"color": "primary", "action": {"type": "text", "label": "📖 Подробный"}}
            ],
            [
                {"color": "secondary", "action": {"type": "text", "label": "◀ Назад"}}
            ]
        ]
    }


def handle_message(vk, user_id: int, message: str):
    """Обрабатывает команды от пользователя"""
    msg_lower = message.lower().strip()

    # Команда старт
    if msg_lower in ["/start", "start", "начать", "привет"]:
        register_user(user_id)

        vk.messages.send(
            user_id=user_id,
            message="🤖 Привет! Я NewsAgent - твой персональный новостной бот.\n\n"
                    "📌 Я собираю новости из разных источников и присылаю тебе подборку.\n\n"
                    "📰 Нажми «Новости» - сразу получу подборку\n"
                    "⚙ Нажми «Настройки» - изменю тему или стиль\n"
                    "ℹ Нажми «Помощь» - покажу список команд\n\n"
                    "👇 Нажми на кнопку, чтобы начать!",
            random_id=0,
            keyboard=create_main_keyboard()
        )
        return

    # Получить новости
    if msg_lower in ["📰 новости", "новости"]:
        settings = get_user_settings(user_id)
        if not settings:
            register_user(user_id)
            settings = {"topic": "technology", "style": "formal"}

        vk.messages.send(
            user_id=user_id,
            message="🔄 Собираю свежие новости...\nЭто может занять несколько секунд.",
            random_id=0
        )

        send_news_to_user(vk, user_id, settings["topic"], settings["style"])
        return

    # Настройки
    if msg_lower in ["⚙ настройки", "настройки"]:
        settings = get_user_settings(user_id)
        if not settings:
            register_user(user_id)
            settings = {"topic": "technology", "style": "formal"}

        vk.messages.send(
            user_id=user_id,
            message=f"⚙ Твои настройки:\n\n"
                    f"📂 Тема: {settings['topic']}\n"
                    f"🎨 Стиль: {settings['style']}\n\n"
                    f"Что хочешь изменить?",
            random_id=0,
            keyboard=create_settings_keyboard()
        )
        return

    # Смена темы
    if msg_lower in ["📂 тема", "тема"]:
        vk.messages.send(
            user_id=user_id,
            message="📂 Выбери тему новостей:\n\n"
                    "💻 Технологии - ИИ, нейросети, гаджеты\n"
                    "⚽ Спорт - футбол, хоккей, теннис\n"
                    "📊 Бизнес - экономика, финансы\n"
                    "🔬 Наука - космос, открытия\n"
                    "💻 IT - программирование, разработка",
            random_id=0,
            keyboard=create_topics_keyboard()
        )
        return

    # Обработка выбора темы
    topic_map = {
        "💻 технологии": "technology",
        "технологии": "technology",
        "⚽ спорт": "sport",
        "спорт": "sport",
        "📊 бизнес": "business",
        "бизнес": "business",
        "🔬 наука": "science",
        "наука": "science",
        "💻 it": "it",
        "it": "it"
    }

    for display, topic_key in topic_map.items():
        if msg_lower == display.lower():
            if update_user_topic(user_id, topic_key):
                vk.messages.send(
                    user_id=user_id,
                    message=f"✅ Тема изменена на {topic_key}\n\n"
                            f"📰 Нажми «Новости», чтобы увидеть подборку!",
                    random_id=0,
                    keyboard=create_main_keyboard()
                )
            return

    # Смена стиля
    if msg_lower in ["🎨 стиль", "стиль"]:
        vk.messages.send(
            user_id=user_id,
            message="🎨 Выбери стиль изложения:\n\n"
                    "📋 Официальный - деловой, профессиональный\n"
                    "💬 Неформальный - дружелюбный, с эмодзи\n"
                    "📝 Краткий - только самое важное\n"
                    "📖 Подробный - максимально детально",
            random_id=0,
            keyboard=create_styles_keyboard()
        )
        return

    # Обработка выбора стиля
    style_map = {
        "📋 официальный": "formal",
        "официальный": "formal",
        "💬 неформальный": "casual",
        "неформальный": "casual",
        "📝 краткий": "brief",
        "краткий": "brief",
        "📖 подробный": "detailed",
        "подробный": "detailed"
    }

    for display, style_key in style_map.items():
        if msg_lower == display.lower():
            if update_user_style(user_id, style_key):
                vk.messages.send(
                    user_id=user_id,
                    message=f"✅ Стиль изменён на {STYLES[style_key]['description']}",
                    random_id=0,
                    keyboard=create_main_keyboard()
                )
            return

    # Помощь
    if msg_lower in ["ℹ помощь", "помощь", "/help"]:
        vk.messages.send(
            user_id=user_id,
            message="ℹ Помощь по командам:\n\n"
                    "📰 Новости - получить свежую подборку\n"
                    "⚙ Настройки - изменить тему или стиль\n"
                    "📂 Тема - выбрать категорию новостей\n"
                    "🎨 Стиль - выбрать стиль изложения\n"
                    "◀ Назад - вернуться в главное меню\n\n"
                    "🔄 Бот обновляет новости каждый час\n\n"
                    "❓ Есть вопросы? Пиши разработчику!",
            random_id=0,
            keyboard=create_main_keyboard()
        )
        return

    # Назад
    if msg_lower in ["◀ назад", "назад"]:
        vk.messages.send(
            user_id=user_id,
            message="◀ Вернулись в главное меню",
            random_id=0,
            keyboard=create_main_keyboard()
        )
        return

    # Ответ по умолчанию
    vk.messages.send(
        user_id=user_id,
        message="❓ Не понял команду.\n\n"
                "Нажми на кнопку или введи:\n"
                "• «Новости» - получить подборку\n"
                "• «Настройки» - изменить параметры\n"
                "• «Помощь» - список команд",
        random_id=0,
        keyboard=create_main_keyboard()
    )


# ========== ЗАПУСК БОТА ==========
def run_vk_bot():
    """Запускает VK-бота в режиме Long Poll"""
    init_db()

    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)

    print("=" * 50)
    print("🤖 VK-бот NewsAgent запущен!")
    print(f"📱 ID группы: {GROUP_ID}")
    print("⏳ Ожидание сообщений...")
    print("=" * 50)

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            if event.object.message:
                user_id = event.object.message['from_id']
                message = event.object.message['text']
                print(f"[MSG] От {user_id}: {message[:50]}")
                handle_message(vk, user_id, message)


# ========== ФОНОВЫЙ ПОСТИНГ ==========
def schedule_news():
    """Фоновый поток для периодической рассылки"""
    time.sleep(30)  # Ждём 30 секунд перед первой рассылкой
    while True:
        print(f"\n⏰ {datetime.now()} - Плановая рассылка новостей")
        send_news_to_all()
        time.sleep(CHECK_INTERVAL)


# ========== ТОЧКА ВХОДА ==========
if __name__ == "__main__":
    # Запуск фонового потока для рассылки
    news_thread = threading.Thread(target=schedule_news, daemon=True)
    news_thread.start()

    # Запуск основного бота
    try:
        run_vk_bot()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")