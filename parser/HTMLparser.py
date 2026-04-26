# HTML-парсер

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from typing import List, Dict, Optional


def parse_html_page(url: str, limit: int = 10) -> List[Dict[str, Optional[str]]]:
    if not url.startswith("http"):
        url = "https://" + url

    try:
        response = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'

        soup = BeautifulSoup(response.text, "html.parser")

        news = []
        seen_links = set()

        # 1. Ищем главную новость (h1)
        h1_tags = soup.find_all("h1")
        for h1 in h1_tags:
            title = h1.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            # Ищем ссылку: внутри h1, или родитель a, или рядом
            link = None
            link_tag = h1.find("a", href=True)
            if link_tag:
                link = link_tag["href"]
            else:
                parent_a = h1.find_parent("a", href=True)
                if parent_a:
                    link = parent_a["href"]

            if link:
                full_link = urljoin(url, link)
                if full_link not in seen_links:
                    news.append({
                        "title": title,
                        "link": full_link,
                        "summary": None,
                        "published": None
                    })
                    seen_links.add(full_link)
                    if len(news) >= limit:
                        return news

        # 2. Ищем по тегу article
        articles = soup.find_all("article")
        for article in articles:
            item = _extract_from_article(article, url)
            if item and item["link"] not in seen_links:
                news.append(item)
                seen_links.add(item["link"])
                if len(news) >= limit:
                    return news

        # 3. Ищем по блокам с новостными классами
        news_selectors = [
            "div.news-item",
            "div.article",
            "div.post",
            "div.item",
            "li.news-item",
            "li.article",
            "div.news",
            "div.entry",
            "div.story",
            "div.card"
        ]

        for selector in news_selectors:
            blocks = soup.select(selector)
            for block in blocks:
                item = _extract_from_block(block, url)
                if item and item["link"] not in seen_links:
                    news.append(item)
                    seen_links.add(item["link"])
                    if len(news) >= limit:
                        return news

        # 4. Ищем по заголовкам h2 и h3
        for tag in ["h2", "h3"]:
            headers = soup.find_all(tag)
            for header in headers:
                title = header.get_text(strip=True)
                if not title or len(title) < 15:
                    continue

                # Ищем ссылку внутри заголовка
                link_tag = header.find("a", href=True)
                if link_tag:
                    link = urljoin(url, link_tag["href"])
                    if link not in seen_links:
                        news.append({
                            "title": title,
                            "link": link,
                            "summary": None,
                            "published": None
                        })
                        seen_links.add(link)
                        if len(news) >= limit:
                            return news

                # Или ссылка рядом
                parent = header.find_parent()
                if parent:
                    link_tag = parent.find("a", href=True)
                    if link_tag and link_tag.get_text(strip=True):
                        link = urljoin(url, link_tag["href"])
                        if link not in seen_links:
                            news.append({
                                "title": title,
                                "link": link,
                                "summary": None,
                                "published": None
                            })
                            seen_links.add(link)
                            if len(news) >= limit:
                                return news

        # 5. Ищем по всем ссылкам с длинным текстом
        all_links = soup.find_all("a", href=True)
        for a in all_links:
            title = a.get_text(strip=True)
            link = a["href"]

            if not title or len(title) < 20:
                continue

            # Пропускаем служебные ссылки
            skip_words = ["login", "signup", "register", "profile", "account",
                          "search", "cookie", "privacy", "terms", "about",
                          "contact", "advert", "banner", "javascript:", "mailto:"]
            link_lower = link.lower()
            if any(word in link_lower for word in skip_words):
                continue

            # Пропускаем ссылки на главную и разделы
            if link in ["/", "/news", "/articles", "/posts", ""]:
                continue

            full_link = urljoin(url, link)
            if full_link not in seen_links:
                news.append({
                    "title": title,
                    "link": full_link,
                    "summary": None,
                    "published": None
                })
                seen_links.add(full_link)
                if len(news) >= limit:
                    break

        return news

    except requests.exceptions.RequestException as e:
        print(f"Ошибка сети при парсинге {url}: {e}")
        return []
    except Exception as e:
        print(f"Ошибка при парсинге {url}: {e}")
        return []


def _extract_from_article(article, base_url: str) -> Optional[Dict[str, Optional[str]]]:
    # Извлекает новость из тега article
    try:
        # Ищем заголовок
        title_tag = article.find(["h1", "h2", "h3", "h4"])
        if not title_tag:
            return None

        title = title_tag.get_text(strip=True)
        if not title or len(title) < 10:
            return None

        # Ищем ссылку
        link_tag = article.find("a", href=True)
        if not link_tag:
            return None

        link = urljoin(base_url, link_tag["href"])

        # Ищем описание
        summary_tag = article.find("p")
        summary = summary_tag.get_text(strip=True) if summary_tag else None
        if summary and len(summary) > 300:
            summary = summary[:300] + "..."

        return {
            "title": title,
            "link": link,
            "summary": summary,
            "published": None
        }
    except Exception:
        return None


def _extract_from_block(block, base_url: str) -> Optional[Dict[str, Optional[str]]]:
    # Извлекает новость из HTML-блока
    try:
        # Ищем ссылку
        link_tag = block.find("a", href=True)
        if not link_tag:
            return None

        # Ищем заголовок
        title_tag = block.find(["h1", "h2", "h3", "h4"]) or link_tag
        title = title_tag.get_text(strip=True)

        if not title or len(title) < 10:
            return None

        link = urljoin(base_url, link_tag["href"])

        # Ищем описание
        summary_tag = block.find("p")
        summary = summary_tag.get_text(strip=True) if summary_tag else None
        if summary and len(summary) > 300:
            summary = summary[:300] + "..."

        return {
            "title": title,
            "link": link,
            "summary": summary,
            "published": None
        }
    except Exception:
        return None


# Тестирование
if __name__ == "__main__":
    test_sites = [
        "https://lenta.ru",
        "https://habr.com/ru/articles/",
        "https://ria.ru/lenta/",
    ]

    print("Тестирование HTML-парсера")

    for site in test_sites:
        print(f"\nИсточник: {site}")

        news = parse_html_page(site, limit=5)

        if not news:
            print("Новости не найдены")
            continue

        for i, item in enumerate(news, 1):
            print(f"\n{i}. {item['title']}")
            print(f"Ссылка на источник: {item['link']}")
            if item['summary']:
                print(f"Описание: {item['summary'][:100]}...")
