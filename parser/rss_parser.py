# Парсер для RSS-лент

import feedparser
from typing import List, Dict

def get_news_from_rss(url: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    Парсит RSS-ленту и возвращает список новостей.
    """
    news_list = []
    try:
        feed = feedparser.parse(url)

        if feed.bozo:
            print(f"Предупреждение во время извлечения по ссылке {url}: {feed.bozo_exception}")

        for entry in feed.entries[:limit]:
            # Дата публикации
            published = entry.get("published", "")
            if not published:
                published = entry.get("pubDate", "")
            if not published:
                published = entry.get("date", "")

            news_item = {
                "title": entry.get("title", "Без заголовка"),
                "link": entry.get("link", ""),
                "published": published,
            }
            news_list.append(news_item)

    except Exception as e:
        print(f"Сбой во время извлечения по ссылке {url}: {e}")
        return []

    return news_list


def get_news_from_multiple_rss(sources: List[str], limit: int = 5) -> List[Dict[str, str]]:
    all_news = []

    for url in sources:
        news = get_news_from_rss(url, limit)
        all_news.extend(news)

    return all_news


# Тестирование
if __name__ == "__main__":
    test_sources = [
        "https://lenta.ru/rss/news",
        "https://habr.com/ru/rss/all/",
        "https://ria.ru/export/rss2/index.xml",
    ]
    print("Тестирование RSS-парсера для массива ссылок:")

    news1 = get_news_from_multiple_rss(test_sources, limit=3)
    for i, item in enumerate(news1, 1):
        print(f"\n{i}. {item['title']}")
        print(f"Дата публикации: {item['published']}")
        print(f"Ссылка на источник: {item['link']}")

    print("Тестирование RSS-парсера для отдельной ссылки:")

    for url in test_sources:
        print(f"\nИсточник: {url}")

        news2 = get_news_from_rss(url, limit=3)

        for i, item in enumerate(news2, 1):
            print(f"\n{i}. {item['title']}")
            print(f"Дата публикации: {item['published']}")
            print(f"Ссылка на источник: {item['link']}")

