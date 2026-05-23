# vk_bot.py
# VK-бот NewsAgent v4.0 — гибкое расписание с разным временем по дням

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import random
import os
import sys
import json
import threading
import time
import re
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import run_agent
from qa_agent import ask_question
from filter import clear_sent_cache, get_cache_size

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = os.getenv("VK_GROUP_ID", "237717966")

if not VK_TOKEN:
    print("❌ Ошибка: не найден VK_TOKEN в файле .env")
    sys.exit(1)

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

# ============================================================
# НАСТРОЙКИ ТЕМ
# ============================================================

TOPICS = {
    "технологии": {
        "name": "🤖 Технологии и ИИ",
        "keywords": [
            "технологии", "искусственный интеллект", "нейросети",
            "машинное обучение", "программирование", "IT", "гаджеты", "роботы", "компьютер", "смартфон", "приложение",
            "софт", "программа",
            "интернет", "сайт", "онлайн", "цифровой", "электронный",
            "разработка", "создали", "запустили", "представили", "выпустили",
            "новый", "технологичный", "инновационный", "современный"
        ],
        "description": "новости про технологии, искусственный интеллект и программирование",
        "threshold": 0.25
    },
    "спорт": {
        "name": "⚽ Спорт",
        "keywords": [
            "спорт", "футбол", "хоккей", "баскетбол", "теннис", "матч", "игра", "победа", "кубок", "лига", "тренер"
        ],
        "description": "спортивные новости, результаты матчей, турниры",
        "threshold": 0.1
    },
    "наука": {
        "name": "🔬 Наука",
        "keywords": [
            "наука", "исследование", "ученые", "открытие", "эксперимент",
            "космос", "физика", "химия", "биология", "медицина",
            "вакцина", "генетика", "мкс", "ракета", "телескоп",
            "ДНК", "РНК", "клетка", "мозг", "нейрон", "эволюция",
            "астрономия", "галактика", "планета", "звезда", "астероид",
            "лаборатория", "институт", "университет", "научный",
            "лауреат", "нобелевская премия", "публикация", "журнал"
        ],
        "description": "научные открытия, исследования, достижения науки",
        "threshold": 0.2
    },
    "политика": {
        "name": "🏛️ Политика",
        "keywords": [
            "политика", "президент", "правительство", "выборы",
            "закон", "депутат", "санкции", "госдума", "кремль",
            "путин", "владимир путин", "указ", "постановление", "министр",
            "кабинет министров", "совет федерации", "парламент", "фракция",
            "единая россия", "кпрф", "лдпр", "справедливая россия",
            "встреча", "переговоры", "визит", "дипломат", "посол",
            "договор", "соглашение", "меморандум", "заявление",
            "законопроект", "поправки", "конституция", "голосование",
            "дума", "совет", "комитет", "комиссия", "аппарат",
            "администрация", "внешняя политика", "международные отношения",
            "брифинг", "пресс-конференция", "интервью", "выступление"
        ],
        "description": "политические новости, международные отношения, законы",
        "threshold": 0.25
    },
    "экономика": {
        "name": "💼 Экономика",
        "keywords": [
            "экономика", "бизнес", "финансы", "инвестиции", "акции",
            "биржа", "банк", "валюта", "рынок", "компания",
            "нефть", "газ", "цена нефти", "баррель", "экспорт", "импорт",
            "торговля", "санкции экономические", "импортозамещение",
            "курс рубля", "доллар", "евро", "юань", "биткоин",
            "криптовалюта", "инфляция", "ставка цб", "ключевая ставка",
            "центробанк", "минфин", "налог", "пошлина", "тариф",
            "бюджет", "дефицит", "профицит", "доходы", "расходы",
            "госдолг", "ввп", "валовый продукт", "производство",
            "промышленность", "сельское хозяйство", "апк", "сфера услуг",
            "предприятие", "фабрика", "завод", "производство",
            "безработица", "зарплата", "пенсия", "соцвыплаты",
            "льготы", "субсидии", "дотации", "поддержка бизнеса"
        ],
        "description": "экономические новости, бизнес, финансы",
        "threshold": 0.25
    }
}

# Хранилище настроек
USER_SETTINGS_FILE = "user_settings.json"


def load_user_settings() -> Dict:
    try:
        with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def save_user_settings(settings: Dict):
    with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


user_settings = load_user_settings()
user_states = {}


def get_user_topic(user_id: int) -> str:
    uid = str(user_id)
    if uid in user_settings and 'topic' in user_settings[uid]:
        return user_settings[uid]['topic']
    return "технологии"


def get_user_schedule(user_id: int) -> Optional[Dict]:
    uid = str(user_id)
    if uid in user_settings and 'schedule' in user_settings[uid]:
        return user_settings[uid]['schedule']
    return None


def has_active_schedule(user_id: int) -> bool:
    schedule = get_user_schedule(user_id)
    return schedule is not None and schedule.get('enabled', False) and bool(schedule.get('rules'))


def format_schedule_info(user_id: int) -> str:
    """Красиво форматирует расписание для показа пользователю"""
    schedule = get_user_schedule(user_id)
    if not schedule or not schedule.get('enabled'):
        return "📅 Рассылка не настроена"

    rules = schedule.get('rules', [])
    if not rules:
        return "📅 Рассылка не настроена"

    days_list = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    lines = ["📅 Рассылка активна\n"]

    for rule in rules:
        days_str = ", ".join(days_list[d] for d in rule['days'])
        lines.append(f"📆 {days_str} — ⏰ {rule['time']}")

    return "\n".join(lines)


# ============================================================
# КЛАВИАТУРЫ
# ============================================================

def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("Новости", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("Все темы", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("Моя тема", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("Рассылка", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("Спросить", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("Помощь", color=VkKeyboardColor.SECONDARY)
    return keyboard


def get_style_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Кратко", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("Подробно", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("Назад", color=VkKeyboardColor.NEGATIVE)
    return keyboard


def get_topics_keyboard():
    keyboard = VkKeyboard(one_time=True)
    for topic_key, topic_info in TOPICS.items():
        keyboard.add_button(topic_info['name'], color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
    keyboard.add_button("Назад", color=VkKeyboardColor.NEGATIVE)
    return keyboard


def get_schedule_keyboard(user_id: int):
    """Клавиатура рассылки: разные кнопки в зависимости от статуса подписки"""
    keyboard = VkKeyboard(one_time=False)

    if has_active_schedule(user_id):
        keyboard.add_button("Изменить расписание", color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button("Моё расписание", color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button("Отписаться от рассылки", color=VkKeyboardColor.NEGATIVE)
    else:
        keyboard.add_button("Подписаться на рассылку", color=VkKeyboardColor.POSITIVE)
        keyboard.add_line()
        keyboard.add_button("Моё расписание", color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button("Отписаться от рассылки", color=VkKeyboardColor.NEGATIVE)

    keyboard.add_line()
    keyboard.add_button("Назад", color=VkKeyboardColor.SECONDARY)
    return keyboard


def get_days_keyboard(selected_days: List[int] = None):
    if selected_days is None:
        selected_days = []

    days = [
        ("Пн", 0), ("Вт", 1), ("Ср", 2),
        ("Чт", 3), ("Пт", 4), ("Сб", 5), ("Вс", 6)
    ]

    keyboard = VkKeyboard(one_time=True)

    for i, (label, day) in enumerate(days):
        prefix = "✅ " if day in selected_days else ""
        color = VkKeyboardColor.POSITIVE if day in selected_days else VkKeyboardColor.PRIMARY
        keyboard.add_button(f"{prefix}{label}", color=color)
        if i == 3:
            keyboard.add_line()

    keyboard.add_line()
    keyboard.add_button("Готово (дни выбраны)", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("Отмена настройки", color=VkKeyboardColor.NEGATIVE)
    return keyboard


def get_time_keyboard():
    keyboard = VkKeyboard(one_time=True)
    hours = ["07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "14:00", "16:00", "18:00", "20:00"]

    for i, h in enumerate(hours):
        if i % 3 == 0 and i > 0:
            keyboard.add_line()
        keyboard.add_button(h, color=VkKeyboardColor.PRIMARY)

    keyboard.add_line()
    keyboard.add_button("Своё время (ввести)", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("Отмена настройки", color=VkKeyboardColor.NEGATIVE)
    return keyboard


def get_edit_schedule_keyboard():
    """Клавиатура для редактирования существующего расписания"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Добавить правило", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("Удалить правило", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("Очистить всё", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("Назад", color=VkKeyboardColor.SECONDARY)
    return keyboard


# ============================================================
# ОТПРАВКА СООБЩЕНИЙ
# ============================================================

def send_message(user_id, text, keyboard=None):
    try:
        keyboard_json = keyboard.get_keyboard() if keyboard else None

        if len(text) > 4000:
            parts = [text[i:i + 4000] for i in range(0, len(text), 4000)]
            for i, part in enumerate(parts):
                vk.messages.send(
                    user_id=user_id,
                    message=part,
                    random_id=random.randint(1, 2 ** 31),
                    keyboard=keyboard_json if i == 0 else None
                )
        else:
            vk.messages.send(
                user_id=user_id,
                message=text,
                random_id=random.randint(1, 2 ** 31),
                keyboard=keyboard_json
            )
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")


# ============================================================
# ПЛАНИРОВЩИК
# ============================================================

def send_scheduled_news(user_id: int):
    try:
        topic_key = get_user_topic(user_id)
        topic_config = TOPICS.get(topic_key, TOPICS["технологии"])

        digest = run_agent(
            style="brief",
            for_telegram=True,
            limit_per_source=2,
            custom_keywords=topic_config["keywords"],
            custom_topic=topic_config["description"],
            custom_threshold=topic_config.get("threshold", 0.08),
            use_dedup_cache=True
        )

        send_message(
            user_id,
            f"📅 Авторассылка\n🏷️ {topic_config['name']}\n\n{digest}"
        )

    except Exception as e:
        logger.error(f"Ошибка рассылки: {e}")


def check_schedules():
    """Проверяет все правила всех пользователей и рассылает новости"""
    settings = load_user_settings()
    now = datetime.now()
    current_day = now.weekday()
    current_time = now.strftime("%H:%M")

    for uid, config in settings.items():
        user_id = int(uid)
        schedule_config = config.get('schedule')

        if not schedule_config or not schedule_config.get('enabled'):
            continue

        rules = schedule_config.get('rules', [])
        for rule in rules:
            if current_day not in rule.get('days', []):
                continue
            if rule.get('time') == current_time:
                # Проверяем, не отправляли ли уже в эту минуту
                last_sent = schedule_config.get('last_sent', {})
                rule_key = f"{current_day}_{current_time}"

                if last_sent.get(rule_key) == now.strftime("%Y-%m-%d"):
                    continue  # Уже отправляли сегодня

                logger.info(f"Рассылка для {user_id}, правило: {rule}")
                send_scheduled_news(user_id)

                # Обновляем last_sent
                if uid not in user_settings:
                    user_settings[uid] = {}
                if 'schedule' not in user_settings[uid]:
                    user_settings[uid]['schedule'] = schedule_config

                if 'last_sent' not in user_settings[uid]['schedule']:
                    user_settings[uid]['schedule']['last_sent'] = {}

                user_settings[uid]['schedule']['last_sent'][rule_key] = now.strftime("%Y-%m-%d")
                save_user_settings(user_settings)
                break  # Отправили по одному правилу, выходим


def scheduler_loop():
    while True:
        try:
            check_schedules()
        except Exception as e:
            logger.error(f"Ошибка планировщика: {e}")
        time.sleep(60)


# ============================================================
# НОРМАЛИЗАЦИЯ ТЕКСТА КОМАНД
# ============================================================

def normalize_text(text: str) -> str:
    # Оставляем двоеточие для времени и дефис для дат
    cleaned = re.sub(r'[^\w\sа-яА-ЯёЁ:\-]', '', text)
    return cleaned.lower().strip()


# ============================================================
# ОБРАБОТЧИК СООБЩЕНИЙ
# ============================================================

def handle_message(user_id, message_text):
    if user_id in user_states:
        process_state(user_id, message_text)
        return

    msg = message_text.strip()
    msg_lower = msg.lower()
    msg_clean = normalize_text(msg)

    logger.info(f"Получено: '{msg}' -> normalized: '{msg_clean}'")

    # ВСЕ ТЕМЫ
    if msg_clean == "все темы":
        send_message(user_id, "🔍 Собираю новости по всем темам... (может занять минуту)")
        try:
            from agent import run_agent_all_topics
            digest = run_agent_all_topics(
                style="brief",
                for_telegram=True,
                limit_per_source=2,
                max_news_per_topic=2
            )
            send_message(user_id, digest, get_main_keyboard())
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            send_message(user_id, "❌ Ошибка при сборе новостей. Попробуй позже.", get_main_keyboard())
        return

    # ПРИВЕТСТВИЕ
    if msg_clean in ["начать", "старт", "привет", "start"]:
        topic_key = get_user_topic(user_id)
        topic_name = TOPICS[topic_key]['name']
        schedule_info = format_schedule_info(user_id)
        cache_size = get_cache_size()

        send_message(
            user_id,
            f"🤖 Привет! Я новостной бот.\n\n"
            f"🏷️ Твоя тема: {topic_name}\n"
            f"📊 В кэше: {cache_size} новостей\n\n"
            f"📌 Кнопки:\n"
            f"• Новости — получить новости по твоей теме\n"
            f"• Все темы — новости по всем темам сразу\n"
            f"• Моя тема — выбрать другую тему\n"
            f"• Рассылка — настроить автоматическую рассылку\n"
            f"• Спросить — задать вопрос нейросети\n"
            f"• Помощь — информация о боте\n\n"
            f"{schedule_info}\n\n"
            f"🕒 {datetime.now().strftime('%H:%M')}",
            get_main_keyboard()
        )
        return

    # ПОМОЩЬ
    if msg_clean in ["помощь", "help"]:
        cache_size = get_cache_size()
        send_message(
            user_id,
            "🤖 NewsAgent — бот для сбора и пересказа новостей\n\n"
            "📌 Возможности:\n"
            "• Новости — получить новости по выбранной теме (Кратко или Подробно)\n"
            "• Все темы — новости по всем темам сразу\n"
            "• Моя тема — выбрать тему (Технологии, Спорт, Наука, Политика, Экономика)\n"
            "• Рассылка — настроить авторассылку по дням и времени\n"
            "   (можно разное время на разные дни!)\n"
            "• Спросить — задать вопрос нейросети\n\n"
            f"📊 В кэше: {cache_size} новостей\n"
            "💡 Кэш очищается каждые 2 часа\n\n"
            "Стили пересказа: Кратко / Подробно\n\n"
            "📝 Для вопросов пиши: Спросить [текст вопроса]",
            get_main_keyboard()
        )
        return

    # НОВОСТИ
    if msg_clean == "новости":
        send_message(user_id, "📰 Выбери стиль пересказа:", get_style_keyboard())
        return

    # СТИЛИ НОВОСТЕЙ
    style_map = {
        "кратко": "brief",
        "подробно": "detailed"
    }

    if msg_clean in style_map:
        style = style_map[msg_clean]
        topic_key = get_user_topic(user_id)
        topic_config = TOPICS[topic_key]

        send_message(user_id, f"🔍 Собираю новости: {topic_config['name']}...")

        try:
            digest = run_agent(
                style=style,
                for_telegram=True,
                limit_per_source=3,
                custom_keywords=topic_config["keywords"],
                custom_topic=topic_config["description"],
                custom_threshold=topic_config.get("threshold", 0.08),
                use_dedup_cache=False
            )
            send_message(user_id, f"🏷️ {topic_config['name']}\n\n{digest}", get_main_keyboard())

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            send_message(user_id, f"❌ Ошибка при сборе новостей. Попробуй позже.", get_main_keyboard())
        return

    # МОЯ ТЕМА
    if msg_clean in ["моя тема", "тема"]:
        current_key = get_user_topic(user_id)
        current_name = TOPICS[current_key]['name']
        send_message(
            user_id,
            f"🏷️ Текущая тема: {current_name}\n\nВыбери новую тему:",
            get_topics_keyboard()
        )
        return

    # ВЫБОР ТЕМЫ
    for topic_key, topic_info in TOPICS.items():
        if msg_clean == normalize_text(topic_info['name']) or msg_clean == topic_key:
            uid = str(user_id)
            if uid not in user_settings:
                user_settings[uid] = {}
            user_settings[uid]['topic'] = topic_key
            save_user_settings(user_settings)

            send_message(
                user_id,
                f"✅ Тема изменена на {topic_info['name']}",
                get_main_keyboard()
            )
            return

    # РАССЫЛКА
    if msg_clean in ["рассылка", "рассылка новостей"]:
        info = format_schedule_info(user_id)
        send_message(user_id, info, get_schedule_keyboard(user_id))
        return

    # ПОДПИСКА / ИЗМЕНИТЬ РАСПИСАНИЕ
    if msg_clean in ["подписаться на рассылку", "подписаться", "изменить расписание"]:
        if has_active_schedule(user_id):
            # Редактирование существующего
            send_message(
                user_id,
                "✏️ Редактирование расписания\n\n"
                "Текущее расписание:\n" + format_schedule_info(user_id).replace("📅 Рассылка активна\n", "") + "\n\n"
                                                                                                              "Что хочешь сделать?",
                get_edit_schedule_keyboard()
            )
            user_states[user_id] = {
                "state": "editing_schedule",
                "data": {"action": None}
            }
        else:
            # Новая подписка
            user_states[user_id] = {
                "state": "choosing_days",
                "data": {"rules": [], "current_rule": {"selected_days": []}}
            }
            send_message(
                user_id,
                "📆 Настройка рассылки\n\n"
                "Шаг 1/2: Выбери дни недели (нажимай на кнопки):\n"
                "Затем нажми «Готово»",
                get_days_keyboard([])
            )
        return

    # МОЁ РАСПИСАНИЕ
    if msg_clean in ["моё расписание", "мое расписание", "расписание"]:
        info = format_schedule_info(user_id)
        send_message(user_id, info, get_schedule_keyboard(user_id))
        return

    # ОТПИСКА
    if msg_clean in ["отписаться от рассылки", "отписаться"]:
        uid = str(user_id)
        if uid in user_settings and 'schedule' in user_settings[uid]:
            user_settings[uid]['schedule']['enabled'] = False
            save_user_settings(user_settings)
            send_message(user_id, "❌ Рассылка отключена.", get_main_keyboard())
        else:
            send_message(user_id, "У тебя нет активной рассылки.", get_main_keyboard())
        return

    # СПРОСИТЬ
    if msg_clean.startswith("спросить"):
        question = msg.replace("Спросить", "").replace("спросить", "").strip()
        if not question:
            send_message(user_id, "❓ Напиши вопрос. Например: Спросить что такое нейросеть?")
            return

        send_message(user_id, "🔎 Ищу ответ...")
        try:
            answer = ask_question(question)
            send_message(user_id, answer, get_main_keyboard())
        except Exception as e:
            send_message(user_id, f"❌ Ошибка: {e}", get_main_keyboard())
        return

    # НАЗАД
    if msg_clean == "назад":
        send_message(user_id, "🔙 Главное меню:", get_main_keyboard())
        return

    # НЕИЗВЕСТНАЯ КОМАНДА
    send_message(
        user_id,
        "🤔 Не понял команду. Используй кнопки меню:\n"
        "• Новости — получить новости\n"
        "• Все темы — все новости сразу\n"
        "• Моя тема — сменить тему\n"
        "• Рассылка — настроить расписание\n"
        "• Спросить — задать вопрос нейросети\n"
        "• Помощь — информация о боте",
        get_main_keyboard()
    )


# ============================================================
# ОБРАБОТКА СОСТОЯНИЙ (настройка рассылки)
# ============================================================

def process_state(user_id, msg):
    state = user_states[user_id]
    msg_clean = normalize_text(msg)
    msg_text = msg.strip()

    if msg_clean in ["отмена настройки", "отмена"]:
        del user_states[user_id]
        send_message(user_id, "❌ Настройка отменена.", get_main_keyboard())
        return

    if state["state"] == "editing_schedule":
        handle_edit_schedule(user_id, msg_clean, state)
    elif state["state"] == "choosing_days":
        handle_day_selection(user_id, msg_clean, state)
    elif state["state"] == "choosing_time":
        handle_time_selection(user_id, msg_clean, state)
    elif state["state"] == "choosing_custom_time":
        handle_custom_time(user_id, msg_text, state)
    elif state["state"] == "confirm_add_rule":
        handle_confirm_add_rule(user_id, msg_clean, state)
    elif state["state"] == "delete_rule":
        handle_delete_rule(user_id, msg_clean, state)


def handle_edit_schedule(user_id, msg_clean, state):
    """Обработка редактирования расписания"""
    if msg_clean in ["добавить правило"]:
        # Загружаем существующие правила, если есть
        uid = str(user_id)
        existing_rules = []
        if uid in user_settings and 'schedule' in user_settings[uid]:
            existing_rules = user_settings[uid]['schedule'].get('rules', [])

        # Инициализируем state с существующими правилами!
        state["state"] = "choosing_days"
        state["data"] = {
            "rules": existing_rules.copy(),
            "current_rule": {"selected_days": []}
        }

        # Показываем, какие дни уже заняты
        occupied_days = set()
        for rule in existing_rules:
            occupied_days.update(rule["days"])

        days_list = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        occupied_str = ", ".join(days_list[d] for d in sorted(occupied_days)) if occupied_days else "нет"

        send_message(
            user_id,
            f"📆 Добавление нового правила\n\n"
            f"Уже занятые дни: {occupied_str}\n"
            f"Выбери дни для нового правила:",
            get_days_keyboard([])
        )
        return

    if msg_clean in ["удалить правило"]:
        schedule = get_user_schedule(user_id)
        rules = schedule.get('rules', []) if schedule else []

        if not rules:
            send_message(user_id, "❌ Нет правил для удаления.", get_edit_schedule_keyboard())
            return

        # Показываем правила для удаления
        days_list = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        lines = ["Выбери правило для удаления:\n"]

        for i, rule in enumerate(rules, 1):
            days_str = ", ".join(days_list[d] for d in rule['days'])
            lines.append(f"{i}. {days_str} — {rule['time']}")

        state["state"] = "delete_rule"
        send_message(user_id, "\n".join(lines), get_delete_rule_keyboard(len(rules)))
        return

    if msg_clean in ["очистить всё"]:
        uid = str(user_id)
        if uid in user_settings and 'schedule' in user_settings[uid]:
            user_settings[uid]['schedule'] = {
                "rules": [],
                "enabled": False,
                "last_sent": {}
            }
            save_user_settings(user_settings)

        send_message(user_id, "🗑️ Все правила удалены.", get_main_keyboard())
        del user_states[user_id]
        return

    if msg_clean == "назад":
        del user_states[user_id]
        send_message(user_id, "🔙 Главное меню:", get_main_keyboard())
        return


def get_delete_rule_keyboard(count: int):
    keyboard = VkKeyboard(one_time=True)
    for i in range(1, count + 1):
        keyboard.add_button(f"Удалить {i}", color=VkKeyboardColor.NEGATIVE)
        if i % 3 == 0:
            keyboard.add_line()
    keyboard.add_line()
    keyboard.add_button("Отмена настройки", color=VkKeyboardColor.SECONDARY)
    return keyboard


def handle_delete_rule(user_id, msg_clean, state):
    """Удаление конкретного правила"""
    match = re.match(r'^удалить\s+(\d+)$', msg_clean)
    if not match:
        send_message(user_id, "❌ Выбери номер правила из списка.")
        return

    rule_num = int(match.group(1)) - 1
    uid = str(user_id)

    if uid not in user_settings or 'schedule' not in user_settings[uid]:
        send_message(user_id, "❌ Ошибка: расписание не найдено.", get_main_keyboard())
        del user_states[user_id]
        return

    rules = user_settings[uid]['schedule'].get('rules', [])
    if rule_num < 0 or rule_num >= len(rules):
        send_message(user_id, "❌ Неверный номер правила.", get_main_keyboard())
        del user_states[user_id]
        return

    deleted_rule = rules.pop(rule_num)

    # Если правил не осталось — отключаем рассылку
    if not rules:
        user_settings[uid]['schedule']['enabled'] = False

    save_user_settings(user_settings)

    days_list = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    days_str = ", ".join(days_list[d] for d in deleted_rule['days'])

    send_message(
        user_id,
        f"✅ Удалено правило: {days_str} — {deleted_rule['time']}",
        get_main_keyboard()
    )
    del user_states[user_id]


def handle_day_selection(user_id, msg_clean, state):
    current_rule = state["data"]["current_rule"]
    selected_days = current_rule["selected_days"]

    if msg_clean in ["готово", "готово дни выбраны"]:
        if not selected_days:
            send_message(user_id, "❌ Выбери хотя бы один день!", get_days_keyboard(selected_days))
            return

        state["state"] = "choosing_time"

        days_list = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        days_str = ", ".join(days_list[d] for d in selected_days)
        send_message(
            user_id,
            f"✅ Дни: {days_str}\n\n"
            f"Шаг 2/2: Выбери время для этих дней:",
            get_time_keyboard()
        )
        return

    day_names = {"пн": 0, "вт": 1, "ср": 2, "чт": 3, "пт": 4, "сб": 5, "вс": 6}

    for day_name, day_num in day_names.items():
        if day_name in msg_clean:
            if day_num in selected_days:
                selected_days.remove(day_num)
            else:
                selected_days.append(day_num)

            send_message(
                user_id,
                f"📆 Выбрано дней: {len(selected_days)}",
                get_days_keyboard(selected_days)
            )
            return


def handle_time_selection(user_id, msg_clean, state):
    if msg_clean in ["своё время", "свое время ввести", "своё время ввести"]:
        state["state"] = "choosing_custom_time"
        send_message(user_id, "⏰ Введи время в формате ЧЧ:ММ (например, 09:30):")
        return

    # Принимаем и "07:00" и "0700"
    time_match = re.match(r'^(\d{2})[:]?(\d{2})$', msg_clean)
    if time_match:
        hour, minute = time_match.groups()
        time_str = f"{hour}:{minute}"

        # Защита: если rules не инициализирован — создаём
        if "rules" not in state["data"]:
            state["data"]["rules"] = []

        # Сохраняем правило
        current_rule = state["data"]["current_rule"]
        current_rule["time"] = time_str
        current_rule["days"] = sorted(current_rule["selected_days"])

        # Добавляем к списку правил
        state["data"]["rules"].append(dict(current_rule))

        # Спрашиваем, хочет ли добавить ещё правило
        state["state"] = "confirm_add_rule"

        days_list = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        days_str = ", ".join(days_list[d] for d in current_rule["days"])

        send_message(
            user_id,
            f"✅ Правило добавлено: {days_str} — {time_str}\n\n"
            f"Хочешь добавить ещё одно правило (другие дни/время)?",
            get_yes_no_keyboard()
        )
        return

    # Если не распознали — просим повторить
    send_message(user_id, "❌ Выбери время из списка или нажми «Своё время»", get_time_keyboard())


def get_yes_no_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Да, добавить ещё", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("Нет, сохранить", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("Отмена настройки", color=VkKeyboardColor.NEGATIVE)
    return keyboard


def handle_confirm_add_rule(user_id, msg_clean, state):
    if msg_clean in ["да", "да добавить ещё", "добавить ещё"]:
        # Начинаем новое правило
        state["state"] = "choosing_days"
        state["data"]["current_rule"] = {"selected_days": []}

        # Показываем, какие дни уже заняты
        occupied_days = set()
        for rule in state["data"]["rules"]:
            occupied_days.update(rule["days"])

        days_list = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        occupied_str = ", ".join(days_list[d] for d in sorted(occupied_days)) if occupied_days else "нет"

        send_message(
            user_id,
            f"📆 Новое правило\n\n"
            f"Уже занятые дни: {occupied_str}\n"
            f"Выбери дни для нового правила:",
            get_days_keyboard([])
        )
        return

    if msg_clean in ["нет", "нет сохранить", "сохранить"]:
        # Сохраняем все правила
        save_multi_rule_schedule(user_id, state["data"]["rules"])
        del user_states[user_id]
        return

    if msg_clean in ["отмена настройки", "отмена"]:
        del user_states[user_id]
        send_message(user_id, "❌ Настройка отменена.", get_main_keyboard())
        return


def handle_custom_time(user_id, msg_text, state):
    time_match = re.match(r'^(\d{1,2})[:.](\d{2})$', msg_text.strip())

    if time_match:
        hour, minute = time_match.groups()
        hour = int(hour)
        minute = int(minute)

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            time_str = f"{hour:02d}:{minute:02d}"

            # Защита: если rules не инициализирован — создаём
            if "rules" not in state["data"]:
                state["data"]["rules"] = []

            # Сохраняем правило
            current_rule = state["data"]["current_rule"]
            current_rule["time"] = time_str
            current_rule["days"] = sorted(current_rule["selected_days"])

            state["data"]["rules"].append(dict(current_rule))
            state["state"] = "confirm_add_rule"

            days_list = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            days_str = ", ".join(days_list[d] for d in current_rule["days"])

            send_message(
                user_id,
                f"✅ Правило добавлено: {days_str} — {time_str}\n\n"
                f"Хочешь добавить ещё одно правило (другие дни/время)?",
                get_yes_no_keyboard()
            )
            return

    send_message(user_id, "❌ Неверный формат. Введи время как ЧЧ:ММ (например, 09:30):")


def save_multi_rule_schedule(user_id, rules):
    """Сохраняет расписание с несколькими правилами"""
    uid = str(user_id)

    if uid not in user_settings:
        user_settings[uid] = {}

    # Проверяем пересечение дней между правилами (берём последнее правило для конфликтных дней)
    # или можно объединить — здесь просто сохраняем все правила
    user_settings[uid]['schedule'] = {
        "rules": rules,
        "enabled": True,
        "last_sent": {}
    }

    save_user_settings(user_settings)

    # Формируем красивое сообщение
    days_list = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    lines = ["✅ Рассылка настроена!\n"]

    for rule in rules:
        days_str = ", ".join(days_list[d] for d in rule['days'])
        lines.append(f"📆 {days_str} — ⏰ {rule['time']}")

    lines.append("\nНовости будут приходить автоматически.")

    send_message(user_id, "\n".join(lines), get_main_keyboard())
    logger.info(f"Рассылка для {user_id}: {rules}")


# ============================================================
# ЗАПУСК
# ============================================================

def main():
    print("=" * 50)
    print("🤖 NewsAgent v4.0 ЗАПУЩЕН")
    print("📡 Ожидание сообщений...")
    print("💡 Гибкое расписание: разное время на разные дни")
    print("=" * 50)

    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
    logger.info("Планировщик запущен")

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            message_text = event.text

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] user_{user_id}: {message_text}")

            try:
                handle_message(user_id, message_text)
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                import traceback
                traceback.print_exc()
                try:
                    send_message(user_id, "❌ Ошибка. Попробуй позже.", get_main_keyboard())
                except:
                    pass


if __name__ == "__main__":
    main()