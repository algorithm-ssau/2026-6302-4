# agent.py
# Главный пайплайн новостного агента с нейросетевым пересказом
# Парсинг → Нормализация → Фильтрация → Дедупликация → Нейропересказ → Форматирование

import logging
from typing import List, Dict, Optional
from datetime import datetime
from filter import filter_exclude_by_topic

from config import (
    KEYWORDS,
    CONTEXT_THRESHOLD,
    TOPIC_DESCRIPTION,
    USE_SENT_CACHE,
    MAX_NEWS_PER_CYCLE,
    DEFAULT_SUMMARY_STYLE,
)

from parser.sources import SourceManager, DEFAULT_SOURCES
from filter import filter_by_keywords, filter_by_context, filter_already_sent
from summarizer import summarize_text

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_all_sources(limit_per_source: int = 5) -> List[Dict]:
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


def normalize_news(news_list: List[Dict]) -> List[Dict]:
    normalized = []

    for news in news_list:
        if not isinstance(news, dict):
            continue

        normalized_item = {
            'title': news.get('title') or '',
            'content': news.get('summary') or news.get('content') or '',
            'url': news.get('link') or news.get('url') or '',
            'link': news.get('link') or '',
            'summary': news.get('summary') or '',
            'published': news.get('published') or '',
        }
        normalized.append(normalized_item)

    logger.info(f"   Нормализовано новостей: {len(normalized)}")
    return normalized


def filter_all_news(news_list: List[Dict],
                    keywords: Optional[List[str]] = None,
                    topic_description: Optional[str] = None,
                    threshold: Optional[float] = None,
                    topic_key: Optional[str] = None) -> List[Dict]:
    logger.info("ФИЛЬТРАЦИЯ")


    if keywords is None:
        keywords = KEYWORDS
    if topic_description is None:
        topic_description = TOPIC_DESCRIPTION
    if threshold is None:
        threshold = CONTEXT_THRESHOLD

    filtered = news_list

    logger.info(f"   Фильтр по ключевым словам: {len(keywords)} ключей")
    try:
        filtered = filter_by_keywords(filtered, keywords)
    except Exception as e:
        logger.error(f"   Ошибка фильтра по ключевым словам: {e}")
    logger.info(f"   После фильтра по ключевым словам: {len(filtered)}")

    if topic_key:
        from filter import filter_exclude_by_topic
        filtered = filter_exclude_by_topic(filtered, topic_key)
        logger.info(f"   После исключения стоп-слов: {len(filtered)}")

    if len(filtered) == 0:
        logger.warning("   ⚠️ Все новости отфильтрованы по ключевым словам!")
        return filtered

    logger.info(f"   Контекстный фильтр (порог: {threshold})")
    try:
        filtered = filter_by_context(filtered, topic_description, threshold=threshold)
    except Exception as e:
        logger.error(f"   Ошибка контекстного фильтра: {e}")
    logger.info(f"   После контекстного фильтра: {len(filtered)}")

    if len(filtered) == 0 and len(news_list) > 0:
        logger.warning("   ⚠️ Контекстный фильтр отсеял все новости!")
        logger.info("   🔄 Возвращаем результаты после фильтра по ключевым словам")
        filtered = filter_by_keywords(news_list, keywords)
    """
    # После контекстного фильтра, перед возвратом
    if keywords:
        #filtered = rank_by_topic_relevance(filtered, keywords)

        # Оставляем только новости с релевантностью > порога
        min_relevance = 1.0
        filtered = [n for n in filtered if n.get('relevance_score', 0) >= min_relevance]
        logger.info(f"   После ранжирования по релевантности: {len(filtered)}")
"""
    return filtered


def deduplicate_news(news_list: List[Dict], use_cache: bool = True) -> List[Dict]:
    logger.info("=" * 60)
    logger.info("ДЕДУПЛИКАЦИЯ")
    logger.info("=" * 60)

    if not use_cache:
        logger.info("   Кэш отключен (ручной запрос)")
        return news_list

    if not USE_SENT_CACHE:
        logger.info("   Кэш отключен в конфигурации")
        return news_list

    logger.info("   Проверка кэша отправленных новостей...")
    try:
        filtered = filter_already_sent(news_list)
        removed_count = len(news_list) - len(filtered)
        logger.info(f"   Новых новостей: {len(filtered)}")
        logger.info(f"   Отфильтровано дубликатов: {removed_count}")

        if len(filtered) == 0 and len(news_list) > 0:
            logger.warning("   ⚠️ Все новости уже были отправлены ранее!")
            logger.info("   🔄 Возвращаем исходный список (кэш переполнен)")
            return news_list

        return filtered
    except Exception as e:
        logger.error(f"   Ошибка дедупликации: {e}")
        return news_list


def limit_news(news_list: List[Dict]) -> List[Dict]:
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


def format_published_time(published_str: str) -> str:
    """Превращает дату в человеко-читаемый вид"""
    if not published_str:
        return "время неизвестно"

    try:
        from dateutil import parser
        dt = parser.parse(str(published_str))
        now = datetime.now()
        diff = now - dt

        if diff.days == 0:
            return f"сегодня в {dt.strftime('%H:%M')}"
        elif diff.days == 1:
            return f"вчера в {dt.strftime('%H:%M')}"
        elif diff.days < 7:
            return f"{diff.days} дня назад"
        else:
            return f"{dt.strftime('%d.%m.%Y')}"
    except Exception:
        return str(published_str)[:16]


def extract_article_text_from_url(url: str) -> str:
    """Извлекает полный текст статьи по ссылке с поддержкой разных сайтов"""
    try:
        import requests
        from bs4 import BeautifulSoup
        import re

        response = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Удаляем мусор
        for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                         "noscript", "meta", "link", "iframe", "button", "form",
                         "div[class*='ad']", "div[class*='banner']", "div[class*='sidebar']"]):
            tag.decompose()

        content = ""

        # 1. Специальная обработка для Habr
        if "habr.com" in url:
            # Ищем статью на Habr
            article_selectors = [
                "div.article-formatted-body",
                "div.post-content",
                "article.content",
                "div.content html-content",
                ".tm-article-body",
                ".article__body"
            ]

            for selector in article_selectors:
                element = soup.select_one(selector)
                if element:
                    # Убираем лишние блоки внутри статьи
                    for bad in element.select(
                            ".article__tags, .article__meta, .post__meta, .voting, .share, .comments, .article__info"):
                        bad.decompose()
                    content = element.get_text(separator="\n", strip=True)
                    if len(content) > 500:
                        break

        # 2. Общие селекторы для всех сайтов
        if not content or len(content) < 200:
            content_selectors = [
                "article", ".article-content", ".post-content", ".story-content",
                ".news-content", ".content", ".entry-content", ".text",
                "[itemprop='articleBody']", "main", ".main-content"
            ]

            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(separator="\n", strip=True)
                    if len(content) > 200:
                        break

        # 3. Если всё ещё нет - берём параграфы
        if not content or len(content) < 200:
            paragraphs = soup.find_all("p")
            text_paragraphs = []
            for p in paragraphs:
                p_text = p.get_text(strip=True)
                # Пропускаем короткие параграфы и мусор
                if len(p_text) > 60 and not any(
                        x in p_text.lower() for x in ['реклама', 'реклама', 'cookie', 'подпишись']):
                    text_paragraphs.append(p_text)

            if text_paragraphs:
                content = "\n\n".join(text_paragraphs)

        if not content:
            return ""

        # Очистка от мусорных фраз
        garbage_phrases = [
            r'Читать\s+далее', r'Подписаться', r'Реклама', r'Поделиться',
            r'Время на прочтение\s+\d+\s+мин', r'Уровень сложности', r'Из песочницы',
            r'\d+\s+минут назад', r'\d+\s+час(?:а|ов)? назад', r'сегодня в \d+:\d+',
            r'вчера в \d+:\d+', r'Охват и читатели\s+\d+', r'Туториал',
            r'\[.*?\]\(.*?\)', r'©.*$'
        ]

        for phrase in garbage_phrases:
            content = re.sub(phrase, '', content, flags=re.IGNORECASE | re.MULTILINE)

        # Нормализация пробелов
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)

        # Ограничиваем длину
        if len(content) > 5000:
            content = content[:5000]

        return content.strip()

    except requests.exceptions.Timeout:
        logger.warning(f"   Таймаут при загрузке {url}")
        return ""
    except Exception as e:
        logger.warning(f"   Ошибка загрузки статьи: {e}")
        return ""


def generate_summary_for_news(news_item: Dict, style: str = None) -> str:
    """Генерирует краткий пересказ новости"""
    if style is None:
        style = DEFAULT_SUMMARY_STYLE

    title = news_item.get('title') or ''
    url = news_item.get('link') or news_item.get('url') or ''
    content = news_item.get('content') or ''
    summary = news_item.get('summary') or ''

    # Если нет контента, но есть ссылка - пробуем извлечь текст со страницы
    if (not content or len(content) < 100) and url:
        logger.info(f"   Извлекаю текст статьи: {url[:60]}...")
        content = extract_article_text_from_url(url)

    # Собираем полный текст для пересказа
    if content and len(content) > 50:
        raw_text = f"{title}\n\n{content}"
    elif summary and len(summary) > 50:
        raw_text = f"{title}\n\n{summary}"
    else:
        raw_text = title

    if not raw_text or len(raw_text.strip()) < 20:
        return title

    try:
        summary_result = summarize_text(raw_text, style=style)

        if summary_result and len(summary_result) > 20:
            logger.info(f"   Пересказ готов: {len(summary_result)} символов")
            return summary_result
        else:
            # Fallback: возвращаем первые 300 символов контента
            if content:
                return content[:300] + ('...' if len(content) > 300 else '')
            return title

    except Exception as e:
        logger.error(f"   Ошибка пересказа: {e}")
        if content:
            return content[:300] + ('...' if len(content) > 300 else '')
        return title


def format_output(news_list: List[Dict], for_telegram: bool = False, style: str = None) -> str:
    """Форматирует новости в единый красивый текст"""
    if style is None:
        style = DEFAULT_SUMMARY_STYLE

    logger.info("=" * 60)
    logger.info("ФОРМАТИРОВАНИЕ ВЫВОДА С НЕЙРОСЕТЕВЫМ ПЕРЕСКАЗОМ")
    logger.info("=" * 60)

    if not news_list:
        if for_telegram:
            return "📭 *Новостей не найдено*\n\nПопробуйте позже или смените тему!"
        else:
            return "📭 Новостей не найдено\n\nПопробуйте позже или смените тему!"

    if for_telegram:
        output = "📰 *Новостная подборка*\n\n"
        output += f"📌 Всего новостей: {len(news_list)}\n"
        output += f"🕒 {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"
        output += "─" * 50 + "\n\n"
    else:
        output = "=" * 60 + "\n"
        output += "📰 НОВОСТНАЯ ПОДБОРКА\n"
        output += "=" * 60 + "\n\n"
        output += f"Всего новостей: {len(news_list)}\n"
        output += f"Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"
        output += "=" * 60 + "\n\n"

    for i, news in enumerate(news_list, 1):
        try:
            title = (news.get('title') or 'Без заголовка').strip()
            link = news.get('link') or news.get('url') or ''
            published_raw = news.get('published') or ''

            logger.info(f"   Генерирую пересказ для: {title[:60]}...")
            summary = generate_summary_for_news(news, style)
            time_str = format_published_time(published_raw)

            if for_telegram:
                output += f"📌 *{i}. {title}*\n"
                if summary:
                    output += f"💬 {summary}\n"
                output += f"🕒 {time_str}\n"
                if link:
                    output += f"🔗 [Источник]({link})\n"
            else:
                output += f"{i}. {title}\n"
                if summary:
                    output += f"   💬 {summary}\n"
                output += f"   🕒 {time_str}\n"
                if link:
                    output += f"   🔗 {link}\n"

            if i < len(news_list):
                output += "\n" + ("─" * 50 if for_telegram else "-" * 50) + "\n\n"
        except Exception as e:
            logger.error(f"Ошибка форматирования новости {i}: {e}")
            continue

    if for_telegram:
        output += "\n" + "─" * 50 + "\n"
        output += "🤖 *Нейросетевой пересказ*\n"
        output += "#NewsBot #ИИ"
    else:
        output += "\n" + "=" * 60 + "\n"
        output += "🤖 Нейросетевой пересказ\n"
        output += "#NewsBot"

    logger.info(f"   Сформирован текст: {len(output)} символов")
    return output


def run_agent(style: str = None,
              for_telegram: bool = False,
              limit_per_source: int = 5,
              custom_keywords: Optional[List[str]] = None,
              custom_topic: Optional[str] = None,
              custom_threshold: Optional[float] = None,
              use_dedup_cache: bool = True) -> str:
    """Запускает полный пайплайн для ОДНОЙ темы"""
    if style is None:
        style = DEFAULT_SUMMARY_STYLE

    logger.info("\n" + "=" * 60)
    logger.info("ЗАПУСК NEWSAGENT ПАЙПЛАЙНА")
    logger.info(f"   Стиль пересказа: {style}")
    logger.info("=" * 60)

    try:
        raw_news = parse_all_sources(limit_per_source=limit_per_source)
        if not raw_news:
            return format_output([], for_telegram, style)

        normalized_news = normalize_news(raw_news)
        if not normalized_news:
            return format_output([], for_telegram, style)

        filtered_news = filter_all_news(
            normalized_news,
            keywords=custom_keywords,
            topic_description=custom_topic,
            threshold=custom_threshold,
        )
        if not filtered_news:
            return format_output([], for_telegram, style)

        deduped_news = deduplicate_news(filtered_news, use_cache=use_dedup_cache)
        if not deduped_news:
            return format_output([], for_telegram, style)

        final_news = limit_news(deduped_news)
        output_text = format_output(final_news, for_telegram, style)

        logger.info("✅ ПАЙПЛАЙН ЗАВЕРШЕН УСПЕШНО")
        return output_text

    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Ошибка: {e}"


def run_agent_all_topics(style: str = None,
                         for_telegram: bool = False,
                         limit_per_source: int = 2,
                         max_news_per_topic: int = 3,
                         use_dedup_cache: bool = True) -> str:
    """
    Запускает пайплайн для ВСЕХ тем сразу.
    Собирает новости по каждой теме и объединяет в один дайджест.
    """
    if style is None:
        style = DEFAULT_SUMMARY_STYLE

    # Импортируем TOPICS здесь, чтобы избежать циклического импорта
    from vk_bot import TOPICS

    logger.info("\n" + "=" * 60)
    logger.info("ЗАПУСК NEWSAGENT ДЛЯ ВСЕХ ТЕМ")
    logger.info("=" * 60)

    all_topics_news = {}

    for topic_key, topic_config in TOPICS.items():
        logger.info(f"\n📌 Обработка темы: {topic_config['name']}")

        try:
            raw_news = parse_all_sources(limit_per_source=limit_per_source)
            if not raw_news:
                logger.warning(f"   Новости не найдены для {topic_key}")
                continue

            normalized_news = normalize_news(raw_news)

            # Для "Всех тем" используем более мягкую фильтрацию
            filtered_news = filter_by_keywords(normalized_news, topic_config["keywords"])

            # Контекстный фильтр отключаем или сильно снижаем порог
            if len(filtered_news) > 5:  # только если много новостей
                filtered_news = filter_by_context(
                    filtered_news,
                    topic_config["description"],
                    threshold=0.01  # очень низкий порог
                )

            if not filtered_news:
                logger.warning(f"   Новости не прошли фильтрацию для {topic_key}")
                continue

            deduped_news = deduplicate_news(filtered_news, use_cache=use_dedup_cache)
            topic_news = deduped_news[:max_news_per_topic]

            if topic_news:
                all_topics_news[topic_key] = topic_news
                logger.info(f"   ✅ Добавлено {len(topic_news)} новостей для {topic_key}")

        except Exception as e:
            logger.error(f"   Ошибка для темы {topic_key}: {e}")
            continue

    if not all_topics_news:
        return "📭 Новостей не найдено ни по одной теме.\n\nПопробуйте позже."

    # Формируем итоговый дайджест
    if for_telegram:
        output = "📰 *ДАЙДЖЕСТ ПО ВСЕМ ТЕМАМ*\n\n"
        output += f"📌 {len(all_topics_news)} тем\n"
        output += f"🕒 {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"
        output += "─" * 50 + "\n\n"
    else:
        output = "=" * 60 + "\n"
        output += "📰 ДАЙДЖЕСТ ПО ВСЕМ ТЕМАМ\n"
        output += "=" * 60 + "\n\n"
        output += f"Тем: {len(all_topics_news)}\n"
        output += f"Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"
        output += "=" * 60 + "\n\n"

    for topic_key, news_list in all_topics_news.items():
        topic_name = TOPICS[topic_key]['name']

        if for_telegram:
            output += f"🏷️ *{topic_name}*\n"
            output += "─" * 30 + "\n\n"
        else:
            output += f"\n🏷️ {topic_name}\n"
            output += "-" * 40 + "\n\n"

        for i, news in enumerate(news_list, 1):
            try:
                title = (news.get('title') or 'Без заголовка').strip()
                link = news.get('link') or news.get('url') or ''

                summary = generate_summary_for_news(news, style)

                if for_telegram:
                    output += f"📌 *{i}. {title}*\n"
                    if summary:
                        output += f"💬 {summary}\n"
                    if link:
                        output += f"🔗 [Источник]({link})\n"
                else:
                    output += f"{i}. {title}\n"
                    if summary:
                        output += f"   💬 {summary}\n"
                    if link:
                        output += f"   🔗 {link}\n"

                output += "\n"
            except Exception as e:
                logger.error(f"Ошибка форматирования: {e}")
                continue

        output += "\n"

    if for_telegram:
        output += "─" * 50 + "\n"
        output += "🤖 *Нейросетевой пересказ*\n"
        output += "#NewsBot #ВсеТемы"
    else:
        output += "=" * 60 + "\n"
        output += "🤖 Нейросетевой пересказ\n"
        output += "#NewsBot"

    return output


if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ АГЕНТА")
    print("=" * 60)

    print("\n📄 ТЕСТ ДЛЯ КОНСОЛИ (одна тема):\n")
    result_console = run_agent(style="detailed", for_telegram=False, limit_per_source=2, use_dedup_cache=False)
    print(result_console)

    print("\n\n📄 ТЕСТ ДЛЯ КОНСОЛИ (ВСЕ ТЕМЫ):\n")
    result_all = run_agent_all_topics(style="brief", for_telegram=False, limit_per_source=1, max_news_per_topic=2,
                                      use_dedup_cache=False)
    print(result_all)
