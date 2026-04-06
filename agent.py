# agent.py
# Главный пайплайн новостного агента
# Парсинг → Фильтрация → Дедупликация → Форматирование → Итоговый список

import logging
from typing import List, Dict
from datetime import datetime

# Импорт конфигурации
from config import (
    KEYWORDS,
    CONTEXT_THRESHOLD,
    TOPIC_DESCRIPTION,
    USE_SENT_CACHE,
    DEFAULT_STYLE,
    STYLES,
    MAX_NEWS_PER_CYCLE,
)

# Импорт менеджера источников
from parser.sources import SourceManager, DEFAULT_SOURCES

# Импорт фильтров
from filter import filter_by_keywords, filter_by_context, filter_already_sent

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ПАРСИНГ =
def parse_all_sources(limit_per_source: int = 5) -> List[Dict]:
    # Собирает новости из всех источников через SourceManager.
    logger.info("=" * 60)
    logger.info("ПАРСИНГ ИСТОЧНИКОВ")
    logger.info("=" * 60)

    manager = SourceManager(DEFAULT_SOURCES)

    logger.info(f"   Всего источников: {len(manager.sources)}")
    enabled_count = sum(1 for s in manager.sources if s.enabled)
    logger.info(f"   Активных источников: {enabled_count}")

    try:
        all_news = manager.fetch_all(limit_per_source=limit_per_source)
        logger.info(f"   ВСЕГО собрано новостей: {len(all_news)}")
        return all_news
    except Exception as e:
        logger.error(f"   Ошибка парсинга: {e}")
        return []


# НОРМАЛИЗАЦИЯ
def normalize_news(news_list: List[Dict]) -> List[Dict]:
    # Приводит все новости к единому формату для фильтров.
    normalized = []

    for news in news_list:
        normalized_item = {
            'title': news.get('title', ''),
            'content': news.get('summary', '') or news.get('content', ''),
            'url': news.get('link', '') or news.get('url', ''),
            'link': news.get('link', ''),
            'summary': news.get('summary', ''),
            'published': news.get('published', ''),
        }
        normalized.append(normalized_item)

    logger.info(f"   Нормализовано новостей: {len(normalized)}")
    return normalized


# ФИЛЬТРАЦИЯ
def filter_all_news(news_list: List[Dict]) -> List[Dict]:
    # Применяет все фильтры к новостям.
    logger.info("=" * 60)
    logger.info("ФИЛЬТРАЦИЯ")
    logger.info("=" * 60)

    filtered = news_list

    # 3.1 Фильтр по ключевым словам
    logger.info(f"   Фильтр по ключевым словам: {len(KEYWORDS)} ключей")
    filtered = filter_by_keywords(filtered, KEYWORDS)
    logger.info(f"   После фильтра по ключевым словам: {len(filtered)}")

    # 3.2 Контекстный фильтр
    logger.info(f"   Контекстный фильтр (порог: {CONTEXT_THRESHOLD})")
    filtered = filter_by_context(filtered, TOPIC_DESCRIPTION, threshold=CONTEXT_THRESHOLD)
    logger.info(f"   После контекстного фильтра: {len(filtered)}")

    return filtered


# ДЕДУПЛИКАЦИЯ
def deduplicate_news(news_list: List[Dict]) -> List[Dict]:
    # Удаляет уже отправленные новости из кэша.
    logger.info("=" * 60)
    logger.info("ДЕДУПЛИКАЦИЯ")
    logger.info("=" * 60)

    if not USE_SENT_CACHE:
        logger.info("  ️ Кэш отключен в конфигурации")
        return news_list

    logger.info("   Проверка кэша отправленных новостей...")
    filtered = filter_already_sent(news_list)

    removed_count = len(news_list) - len(filtered)
    logger.info(f"   Новых новостей: {len(filtered)}")
    logger.info(f"   Отфильтровано дубликатов: {removed_count}")

    return filtered


# ОГРАНИЧЕНИЕ КОЛИЧЕСТВА
def limit_news(news_list: List[Dict]) -> List[Dict]:
    # Ограничивает количество новостей до MAX_NEWS_PER_CYCLE.
    logger.info("=" * 60)
    logger.info("ОГРАНИЧЕНИЕ КОЛИЧЕСТВА")
    logger.info("=" * 60)

    if len(news_list) > MAX_NEWS_PER_CYCLE:
        logger.info(f"   Сокращаем с {len(news_list)} до {MAX_NEWS_PER_CYCLE}")
        limited = news_list[:MAX_NEWS_PER_CYCLE]
    else:
        limited = news_list
        logger.info(f"   Количество в норме: {len(limited)}")

    return limited


# ФОРМАТИРОВАНИЕ ВЫВОДА
def format_output(news_list: List[Dict], style: str = DEFAULT_STYLE, for_telegram: bool = False) -> str:
    # Форматирует новости для вывода в консоль или Telegram бот.
    logger.info("=" * 60)
    logger.info("ФОРМАТИРОВАНИЕ ВЫВОДА")
    logger.info(f"   Стиль: {style}")
    logger.info(f"   Для Telegram: {for_telegram}")

    # Если новостей нет
    if not news_list:
        if for_telegram:
            return " Новостей не найдено_\n\nПопробуйте позже!"
        else:
            return " Новостей не найдено\n\nПопробуйте позже!"

    # Получаем настройки стиля
    style_config = STYLES.get(style, STYLES[DEFAULT_STYLE])

    # Эмодзи для стиля
    emoji_news = "📰 " if style_config.get('emoji', False) else ""
    emoji_time = "⏰ " if style_config.get('include_time', True) else ""
    emoji_link = "🔗 " if style_config.get('include_source', True) else ""

    # Разделитель между новостями
    separator = "\n\n" + "─" * 50 + "\n\n" if for_telegram else "\n" + "=" * 60 + "\n\n"

    # ЗАГОЛОВОК ПОДБОРКИ
    if for_telegram:
        output = f" *Новостная подборка*\n\n"
        output += f" Всего новостей: {len(news_list)}\n"
        output += f" Стиль: {style_config['description']}\n"
        output += f" Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"
        output += "─" * 50 + "\n\n"
    else:
        output = "=" * 60 + "\n"
        output += " НОВОСТНАЯ ПОДБОРКА\n"
        output += "=" * 60 + "\n\n"
        output += f"Всего новостей: {len(news_list)}\n"
        output += f"Стиль: {style_config['description']}\n"
        output += f"Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"
        output += "=" * 60 + "\n\n"

    # СПИСОК НОВОСТЕЙ
    for i, news in enumerate(news_list, 1):
        # Заголовок
        title = news.get('title', 'Без заголовка')
        max_length = style_config.get('max_length', 500)

        if len(title) > max_length:
            title = title[:max_length - 3] + '...'

        if for_telegram:
            output += f"{emoji_news}*{i}. {title}*\n"
        else:
            output += f"{emoji_news}{i}. {title}\n"

        # Время публикации
        if style_config.get('include_time', True):
            published = news.get('published', '')
            if published:
                if for_telegram:
                    output += f"{emoji_time}_{published}_\n"
                else:
                    output += f"{emoji_time}{published}\n"

        # Описание/саммари
        summary = news.get('summary', '') or news.get('content', '')
        if summary:
            if len(summary) > max_length:
                summary = summary[:max_length - 3] + '...'

            if for_telegram:
                output += f"{summary}\n"
            else:
                output += f"   {summary}\n"

        # Ссылка на источник
        if style_config.get('include_source', True):
            link = news.get('link', '') or news.get('url', '')
            if link:
                if for_telegram:
                    output += f"{emoji_link}[Источник]({link})\n"
                else:
                    output += f"{emoji_link}{link}\n"

        # Разделитель между новостями
        if i < len(news_list):
            output += separator
    if for_telegram:
        output += "\n" + "─" * 50 + "\n"
        output += f"\n_Подборка создана автоматически_\n"
        output += f"#NewsAgent #Новости"
    else:
        output += "\n" + "=" * 60 + "\n"
        output += "Подборка создана автоматически\n"
        output += "#NewsAgent #Новости\n"
        output += "=" * 60

    logger.info(f"   Сформирован текст: {len(output)} символов")
    logger.info(f"   Новостей в подборке: {len(news_list)}")

    return output


# ГЛАВНАЯ ФУНКЦИЯ ПАЙПЛАЙНА
def run_agent(style: str = DEFAULT_STYLE, for_telegram: bool = False, limit_per_source: int = 5) -> str:
    # Запускает полный пайплайн обработки новостей.
    logger.info("\n" + "=" * 60)
    logger.info("ЗАПУСК NEWSAGENT ПАЙПЛАЙНА")
    logger.info("=" * 60)

    try:
        # ПАРСИНГ
        raw_news = parse_all_sources(limit_per_source=limit_per_source)

        if not raw_news:
            logger.warning("Новости не найдены на этапе парсинга")
            return format_output([], style, for_telegram)
        # НОРМАЛИЗАЦИЯ
        normalized_news = normalize_news(raw_news)
        #ФИЛЬТРАЦИЯ
        filtered_news = filter_all_news(normalized_news)

        if not filtered_news:
            logger.warning("Новости не прошли фильтрацию")
            return format_output([], style, for_telegram)
        # ДЕДУПЛИКАЦИЯ
        deduped_news = deduplicate_news(filtered_news)

        if not deduped_news:
            logger.warning("Все новости оказались дубликатами")
            return format_output([], style, for_telegram)
        # ОГРАНИЧЕНИЕ КОЛИЧЕСТВА
        final_news = limit_news(deduped_news)
        # ФОРМАТИРОВАНИЕ
        output_text = format_output(final_news, style, for_telegram)
        # ИТОГ
        logger.info("=" * 60)
        logger.info(" ПАЙПЛАЙН ЗАВЕРШЕН УСПЕШНО")
        logger.info("=" * 60)

        return output_text

    except Exception as e:
        logger.error(f" КРИТИЧЕСКАЯ ОШИБКА В ПАЙПЛАЙНЕ: {e}")
        return f" Ошибка: {e}"


# ТЕСТИРОВАНИЕ
if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ПАЙПЛАЙНА AGENT.PY")
    print("=" * 60)

    # Запуск пайплайна для консоли
    print("\nЗАПУСК ДЛЯ КОНСОЛИ:\n")
    result_console = run_agent(style=DEFAULT_STYLE, for_telegram=False, limit_per_source=3)
    print(result_console)

    # Запуск пайплайна для Telegram
    print("\n\nЗАПУСК ДЛЯ TELEGRAM:\n")
    result_telegram = run_agent(style="casual", for_telegram=True, limit_per_source=3)
    print(result_telegram)

    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)