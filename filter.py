# filter.py
# Модуль фильтрации новостей для NewsAgent (исправленный)

from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Глобальный кэш отправленных новостей
SENT_NEWS_CACHE = {}
CACHE_MAX_SIZE = 1000  # Максимальный размер кэша
CACHE_TTL_HOURS = 2  # Время жизни записи в кэше (часов)


def _clean_old_entries():
    """Удаляет старые записи из кэша"""
    now = datetime.now()
    old_keys = []

    for news_id, timestamp in SENT_NEWS_CACHE.items():
        if now - timestamp > timedelta(hours=CACHE_TTL_HOURS):
            old_keys.append(news_id)

    for key in old_keys:
        del SENT_NEWS_CACHE[key]

    if old_keys:
        logger.info(f"   Очищено {len(old_keys)} устаревших записей из кэша")


def _limit_cache_size():
    """Ограничивает размер кэша, удаляя самые старые записи"""
    if len(SENT_NEWS_CACHE) > CACHE_MAX_SIZE:
        # Сортируем по времени и удаляем лишние
        sorted_items = sorted(SENT_NEWS_CACHE.items(), key=lambda x: x[1])
        items_to_remove = len(SENT_NEWS_CACHE) - CACHE_MAX_SIZE

        for news_id, _ in sorted_items[:items_to_remove]:
            del SENT_NEWS_CACHE[news_id]

        logger.info(f"   Кэш переполнен, удалено {items_to_remove} старых записей")


def filter_by_keywords(news_list: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
    """Фильтрует новости по ключевым словам (мягкий режим)"""
    if not keywords:
        logger.info("   Ключевые слова не заданы - возвращаем все новости")
        return news_list

    filtered_news = []
    keywords_lower = [kw.lower() for kw in keywords]

    for news in news_list:
        # Безопасно получаем текст
        title = (news.get('title') or '').lower()
        content = (news.get('content') or '').lower()
        summary = (news.get('summary') or '').lower()

        text_to_check = f"{title} {content} {summary}"

        # Проверяем наличие ключевых слов
        if any(kw in text_to_check for kw in keywords_lower):
            filtered_news.append(news)

    logger.info(f"   Отфильтровано по ключевым словам: {len(filtered_news)} из {len(news_list)}")

    # Если отфильтровали всё - возвращаем исходный список
    if len(filtered_news) == 0 and len(news_list) > 0:
        logger.warning("   ⚠️ Все новости отфильтрованы! Проверьте keywords в config.py")
        # Показываем примеры того, что есть в новостях
        if len(news_list) > 0:
            sample_title = (news_list[0].get('title') or '')[:100]
            logger.info(f"   Пример заголовка: {sample_title}")
            logger.info("   💡 Совет: добавьте слова из заголовков в KEYWORDS")

    return filtered_news


def filter_by_context(news_list: List[Dict], topic_description: str,
                      threshold: float = 0.1) -> List[Dict]:
    """
    Умный фильтр по контексту (смыслу), а не по ключевым словам.
    Использует пониженный порог для лучшего захвата новостей.
    """
    if not news_list or not topic_description:
        return news_list

    # Безопасная конкатенация с заменой None
    texts = []
    for news in news_list:
        title = news.get('title') or ''
        content = news.get('content') or ''
        summary = news.get('summary') or ''
        texts.append(f"{title} {content} {summary}")

    all_texts = [topic_description] + texts

    try:
        vectorizer = TfidfVectorizer(max_features=1000, stop_words=None)
        tfidf_matrix = vectorizer.fit_transform(all_texts)

        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

        # Логируем распределение сходства
        if len(similarities) > 0:
            logger.info(f"   Диапазон сходства: {similarities.min():.3f} - {similarities.max():.3f}")
            logger.info(f"   Среднее сходство: {similarities.mean():.3f}")

        filtered = [news for i, news in enumerate(news_list) if similarities[i] >= threshold]

        logger.info(f"   Отфильтровано по контексту: {len(filtered)} из {len(news_list)}")

        return filtered

    except Exception as e:
        logger.error(f"Ошибка контекстного фильтра: {e}")
        return news_list


def filter_already_sent(news_list: List[Dict]) -> List[Dict]:
    """Исключает новости, которые уже были отправлены ранее"""
    if not news_list:
        return []

    # Очищаем старые записи
    _clean_old_entries()

    new_news = []
    now = datetime.now()

    for news in news_list:
        # Безопасное формирование ID
        title = news.get('title') or ''
        url = news.get('url') or ''
        link = news.get('link') or ''
        news_id = f"{title}|{url}|{link}"

        if news_id not in SENT_NEWS_CACHE:
            SENT_NEWS_CACHE[news_id] = now
            new_news.append(news)

    # Ограничиваем размер кэша
    _limit_cache_size()

    logger.info(f"   В кэше: {len(SENT_NEWS_CACHE)} записей")

    return new_news


def clear_sent_cache():
    """Очищает кэш отправленных новостей"""
    global SENT_NEWS_CACHE
    count = len(SENT_NEWS_CACHE)
    SENT_NEWS_CACHE.clear()
    logger.info(f"Кэш отправленных новостей очищен (удалено {count} записей)")


def get_cache_size() -> int:
    """Возвращает текущий размер кэша"""
    return len(SENT_NEWS_CACHE)