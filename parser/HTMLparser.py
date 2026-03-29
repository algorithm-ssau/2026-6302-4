import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def parse_html_page(url, limit=10):
    if not url.startswith("http"):
        url = "https://" + url

    try:
        response = requests.get(url, timeout=5, headers={
            "User-Agent": "Mozilla/5.0"
        })
        soup = BeautifulSoup(response.text, "html.parser")

        news = []
        seen_links = set()

        # Поиск по тегу article
        articles = soup.find_all("article")

        for article in articles:
            item = extract_from_container(article, url)
            if item:
                if item["link"] not in seen_links:
                    news.append(item)
                    seen_links.add(item["link"])

            if len(news) >= limit:
                return news

        # Поиск по тегу заголовков
        headers = soup.find_all(["h1", "h2", "h3"])

        for h in headers:
            a = h.find_parent("a") or h.find("a")

            if not a:
                continue

            item = extract_from_link(a, url)

            if item and item["link"] not in seen_links:
                news.append(item)
                seen_links.add(item["link"])

            if len(news) >= limit:
                return news

        # Поиск по тегу ссылок
        links = soup.find_all("a")

        for a in links:
            item = extract_from_link(a, url)

            if item and item["link"] not in seen_links:
                news.append(item)
                seen_links.add(item["link"])

            if len(news) >= limit:
                break

        return news

    except Exception as e:
        print("Ошибка:", e)
        return []


def extract_from_container(container, base_url):
    title_tag = container.find(["h1", "h2", "h3"])
    link_tag = container.find("a")

    if not title_tag or not link_tag:
        return None

    title = title_tag.get_text(strip=True)
    link = urljoin(base_url, link_tag.get("href"))

    if not is_valid_news(title, link):
        return None

    summary_tag = container.find("p")
    summary = summary_tag.get_text(strip=True) if summary_tag else None

    return {
        "title": title,
        "link": link,
        "summary": summary,
        "published": None
    }


def extract_from_link(a_tag, base_url):
    title = a_tag.get_text(strip=True)
    link = a_tag.get("href")

    if not link:
        return None

    link = urljoin(base_url, link)

    if not is_valid_news(title, link):
        return None

    return {
        "title": title,
        "link": link,
        "summary": None,
        "published": None
    }


def is_valid_news(title, link):
    if not title or not link:
        return False

    # короткие тексты — мусор
    if len(title) < 20:
        return False

    # мусорные ссылки
    bad_words = ["login", "signup", "advert", "ads", "#"]
    if any(word in link.lower() for word in bad_words):
        return False

    # эвристика "похоже на новость"
    good_patterns = ["news", "article", "202", "/"]
    if not any(p in link.lower() for p in good_patterns):
        return False

    return True

if __name__ == "__main__":
    test_sites = [
        "https://lenta.ru",
        "https://ria.ru",
        "https://www.rbc.ru",
    ]

    print("Тестирование HTML-парсера для массива сайтов:")

    for site in test_sites:
        print(f"\nИсточник: {site}")

        news = parse_html_page(site, limit=5)

        if not news:
            print("Новости не найдены")
            continue

        for i, item in enumerate(news, 1):
            print(f"\n{i}. {item['title']}")
            print(f"Ссылка: {item['link']}")
            print(f"Описание: {item['summary']}")