"""
Фильтрации новостей для NewsAgent
Фильтр по ключевым словам
"""

from typing import List, Dict, Any

def filter_by_keywords(news_list: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:

    if not keywords:
        return news_list

    filtered_news = []
    keywords_lower = [kw.lower() for kw in keywords]

    for news in news_list:
        title = news.get('title', '').lower()
        content = news.get('content', '').lower()

        # Проверяем наличие хотя бы одного ключевого слова в заголовке или содержании
        if any(kw in title or kw in content for kw in keywords_lower):
            filtered_news.append(news)

    return filtered_news

"""
Умный фильтр контекста (похожесть на тему)
Находит новости по смыслу, даже если в них нет прямых ключевых слов
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def filter_by_context(news_list, topic_description, threshold=0.3):
    """
    Фильтрует по смыслу, а не по ключевым словам.
    topic_description - описание темы (например: "новости про искусственный интеллект")
    """
    texts = [f"{news['title']} {news['content']}" for news in news_list]
    all_texts = [topic_description] + texts

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    # Сравниваем каждую новость с описанием темы
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    return [news for i, news in enumerate(news_list) if similarities[i] >= threshold]

"""
Кэширование уже обработанных новостей
Бот не отправляет одну и ту же новость повторно, даже если она снова появилась в ленте.
"""

# Храним ID уже отправленных новостей
SENT_NEWS_CACHE = set()

def filter_already_sent(news_list):
    """Исключает новости, которые уже были отправлены ранее"""
    new_news = []
    for news in news_list:
        news_id = f"{news.get('title')}|{news.get('url')}"
        if news_id not in SENT_NEWS_CACHE:
            SENT_NEWS_CACHE.add(news_id)
            new_news.append(news)
    return new_news
