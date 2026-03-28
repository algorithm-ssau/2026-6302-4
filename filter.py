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
