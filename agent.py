# agent.py
# Главный пайплайн новостного агента
# Парсинг → Фильтрация → Дедупликация → Итоговый список

import logging
from typing import List, Dict

# Импорт конфигурации
from config import (
    KEYWORDS,
    RSS_SOURCES,
    HTML_SOURCES,
    MAX_NEWS_PER_CYCLE,
    MAX_NEWS_PER_SOURCE,
    CONTEXT_THRESHOLD,
    TOPIC_DESCRIPTION,
    USE_SENT_CACHE,
)

# Импорт парсеров
from parser.RSSparser import get_news_from_multiple_rss
from parser.HTMLparser import parse_html_page

# Импорт фильтров
from filter import filter_by_keywords, filter_by_context, filter_already_sent

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# НОРМАЛИЗАЦИЯ ДАННЫХ
def normalize_news(news_list: List[Dict]) -> List[Dict]:

    # Приводит все новости к единому формату для фильтров.
    normalized = []

    for news in news_list:
        normalized_item = {
            'title': news.get('title', ''),
            # filter.py ждёт 'content', но парсеры возвращают 'summary'
            'content': news.get('summary', '') or news.get('content', ''),
            # filter.py ждёт 'url', но парсеры возвращают 'link'
            'url': news.get('link', '') or news.get('url', ''),
            'published': news.get('published', ''),
            # Сохраняем оригинальные поля для дальнейшего использования
            'link': news.get('link', ''),
            'summary': news.get('summary', ''),
        }
        normalized.append(normalized_item)

    return normalized


# ШАГ 1: ПАРСИНГ
def parse_all_sources() -> List[Dict]:
    #Собирает новости из всех источников (RSS + HTML).
    #Возвращает: список всех найденных новостей
    logger.info("=" * 60)
    logger.info("ПАРСИНГ ИСТОЧНИКОВ")
    logger.info("=" * 60)

    all_news = []

    # 1.1 Парсинг RSS-лент
    logger.info(f"   RSS источников: {len(RSS_SOURCES)}")
    try:
        rss_news = get_news_from_multiple_rss(RSS_SOURCES, limit=MAX_NEWS_PER_SOURCE)
        all_news.extend(rss_news)
        logger.info(f"RSS новостей найдено: {len(rss_news)}")
    except Exception as e:
        logger.error(f"Ошибка RSS парсинга: {e}")

    # 1.2 Парсинг HTML-сайтов
    logger.info(f"   HTML источников: {len(HTML_SOURCES)}")
    try:
        for url in HTML_SOURCES[:3]:  # Ограничиваем количество для скорости
            html_news = parse_html_page(url, limit=MAX_NEWS_PER_SOURCE)
            all_news.extend(html_news)
            logger.info(f" HTML новостей с {url}: {len(html_news)}")
    except Exception as e:
        logger.error(f" Ошибка HTML парсинга: {e}")

    logger.info(f" ВСЕГО собрано новостей: {len(all_news)}")
    return all_news


#ФИЛЬТРАЦИЯ
def filter_all_news(news_list: List[Dict]) -> List[Dict]:
    logger.info("=" * 60)
    logger.info("ФИЛЬТРАЦИЯ")
    logger.info("=" * 60)

    filtered = news_list

    # 2.1 Фильтр по ключевым словам
    logger.info(f"   Фильтр по ключевым словам: {len(KEYWORDS)} ключей")
    filtered = filter_by_keywords(filtered, KEYWORDS)
    logger.info(f" После фильтра по ключевым словам: {len(filtered)}")

    # 2.2 Контекстный фильтр
    logger.info(f"   Контекстный фильтр (порог: {CONTEXT_THRESHOLD})")
    logger.info(f"   Тема: {TOPIC_DESCRIPTION[:50]}...")
    filtered = filter_by_context(filtered, TOPIC_DESCRIPTION, threshold=CONTEXT_THRESHOLD)
    logger.info(f"   После контекстного фильтра: {len(filtered)}")

    return filtered


# ДЕДУПЛИКАЦИЯ
def deduplicate_news(news_list: List[Dict]) -> List[Dict]:
    #Удаляет уже отправленные новости из кэша.
    logger.info("=" * 60)
    logger.info("ДЕДУПЛИКАЦИЯ")
    logger.info("=" * 60)

    if not USE_SENT_CACHE:
        logger.info("Кэш отключен в конфигурации")
        return news_list

    logger.info("   Проверка кэша отправленных новостей...")
    filtered = filter_already_sent(news_list)

    removed_count = len(news_list) - len(filtered)
    logger.info(f"    Новых новостей: {len(filtered)}")
    logger.info(f"   ️ Отфильтровано дубликатов: {removed_count}")

    return filtered


# ОГРАНИЧЕНИЕ КОЛИЧЕСТВА
def limit_news(news_list: List[Dict]) -> List[Dict]:
    #Ограничивает количество новостей до MAX_NEWS_PER_CYCLE.
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


#  ГЛАВНАЯ ФУНКЦИЯ ПАЙПЛАЙНА
def run_agent() -> List[Dict]:
    logger.info("\n" + "=" * 60)
    logger.info("ЗАПУСК NEWSAGENT ПАЙПЛАЙНА")
    logger.info("=" * 60)

    try:
        # ПАРСИНГ
        raw_news = parse_all_sources()

        if not raw_news:
            logger.warning(" Новости не найдены на этапе парсинга")
            return []
        # НОРМАЛИЗАЦИЯ
        normalized_news = normalize_news(raw_news)
        logger.info(f"    Нормализовано новостей: {len(normalized_news)}")
        # ФИЛЬТРАЦИЯ
        filtered_news = filter_all_news(normalized_news)

        if not filtered_news:
            logger.warning(" Новости не прошли фильтрацию")
            return []
        # ДЕДУПЛИКАЦИЯ
        deduped_news = deduplicate_news(filtered_news)

        if not deduped_news:
            logger.warning(" Все новости оказались дубликатами")
            return []
        #  ОГРАНИЧЕНИЕ КОЛИЧЕСТВА
        final_news = limit_news(deduped_news)
        # ИТОГ
        logger.info("=" * 60)
        logger.info(" ПАЙПЛАЙН ЗАВЕРШЕН УСПЕШНО")
        logger.info("=" * 60)
        logger.info(f" ИТОГО новостей для отправки: {len(final_news)}")
        logger.info("=" * 60)

        return final_news

    except Exception as e:
        logger.error(f" КРИТИЧЕСКАЯ ОШИБКА В ПАЙПЛАЙНЕ: {e}")
        return []


#ТЕСТИРОВАНИЕ
if __name__ == "__main__":
    print("=" * 60)
    print(" ТЕСТИРОВАНИЕ ПАЙПЛАЙНА AGENT.PY")
    print("=" * 60)

    # Запуск пайплайна
    result = run_agent()

    # Вывод результатов
    print("\n" + "=" * 60)
    print(" РЕЗУЛЬТАТЫ ПАЙПЛАЙНА")
    print("=" * 60)

    if result:
        print(f"\n Найдено {len(result)} новостей:\n")
        for i, news in enumerate(result[:5], 1):  # Показываем первые 5
            print(f"{i}. {news['title']}")
            print(f"   Ссылка: {news['link'][:70]}...")
            print(f"   Дата: {news['published']}")
            print()
    else:
        print("\n Новостей не найдено ")

    print("=" * 60)
    print(" ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)