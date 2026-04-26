# Мульти-источник новостей. Универсальный парсер для RSS и HTML

from typing import List, Dict, Optional, Union
from enum import Enum

# Импортируем наши готовые парсеры
from .rss_parser import get_news_from_rss
from .html_parser import parse_html_page

class SourceType(Enum):
    # Типы источников
    RSS = "rss"
    HTML = "html"
    AUTO = "auto"  # автоматическое определение

class Source:
    # Класс для представления источника новостей

    def __init__(self, name: str, url: str, source_type: SourceType = SourceType.AUTO, enabled: bool = True):
        # Инициализация источника.
        self.name = name
        self.url = url
        self.source_type = source_type
        self.enabled = enabled
        self._detected_type = None  # для AUTO режима

    def detect_source_type(self) -> SourceType:
        # Автоматически определяет тип источника по URL
        url_lower = self.url.lower()

        # Признаки RSS
        rss_patterns = [
            '/rss',
            '/feed',
            '.xml',
            '/export/rss2',
            '/rss/',
        ]

        for pattern in rss_patterns:
            if pattern in url_lower:
                return SourceType.RSS

        # По умолчанию считаем HTML
        return SourceType.HTML

    def fetch(self, limit: int = 5) -> List[Dict[str, Optional[str]]]:
        # Получает новости из источника

        if not self.enabled:
            return []

        # Определяем тип источника
        if self.source_type == SourceType.AUTO:
            actual_type = self.detect_source_type()
        else:
            actual_type = self.source_type

        print(f"Источник: {self.name} ({actual_type.value}): {self.url}")

        # Выбираем парсер
        if actual_type == SourceType.RSS:
            news = get_news_from_rss(self.url, limit)
        else:
            news = parse_html_page(self.url, limit)

        print(f"Извлечено {len(news)} новостей")
        return news

    def __repr__(self) -> str:
        return f"Source(name='{self.name}', type={self.source_type.value}, enabled={self.enabled})"


class SourceManager:
    # Менеджер для управления несколькими источниками

    def __init__(self, sources: Optional[List[Source]] = None):
        # Инициализация менеджера источников.
        self.sources = sources or []

    def add_source(self, source: Source) -> None:
        # Добавляет источник
        self.sources.append(source)
        print(f"Добавлен источник {source.name}")

    def remove_source(self, name: str) -> bool:
        # Удаляет источник по названию
        for i, source in enumerate(self.sources):
            if source.name == name:
                self.sources.pop(i)
                print(f"Удалён источник {name}")
                return True
        return False

    def enable_source(self, name: str, enabled: bool = True) -> bool:
        # Включает/отключает источник
        for source in self.sources:
            if source.name == name:
                source.enabled = enabled
                print(f"{'✔' if enabled else '⨯'} источник: {name}")
                return True
        return False

    def fetch_all(self, limit_per_source: int = 5) -> List[Dict[str, Optional[str]]]:
        # Получает новости из всех включённых источников
        all_news = []

        for source in self.sources:
            if not source.enabled:
                continue

            news = source.fetch(limit_per_source)
            all_news.extend(news)

        return all_news

    def list_sources(self) -> None:
        # Выводит список всех источников
        if not self.sources:
            print("Список источников пуст")
            return

        print("\nСписок источников:")
        for i, source in enumerate(self.sources, 1):
            status = "✔" if source.enabled else "⨯"
            print(f"{i}. {status} {source.name} ({source.source_type.value})")
            print(f"   {source.url}")


# Предопределённые источники
DEFAULT_SOURCES = [
    Source("Lenta.ru (RSS)", "https://lenta.ru/rss/news", SourceType.RSS),
    Source("Habr (RSS)", "https://habr.com/ru/rss/all/", SourceType.RSS),
    Source("РИА Новости (RSS)", "https://ria.ru/export/rss2/index.xml", SourceType.RSS),
    Source("Lenta.ru (HTML)", "https://lenta.ru", SourceType.HTML),
    Source("РБК (HTML)", "https://www.rbc.ru", SourceType.HTML),
    Source("РИА Лента (HTML)", "https://ria.ru/lenta/", SourceType.HTML),
]


class UniversalParser:
    # Универсальный парсер, автоматически выбирающий метод по типу источника

    @staticmethod
    def parse(source: Union[Source, str], limit: int = 5) -> List[Dict[str, Optional[str]]]:
        if isinstance(source, str):
            # Если передана строка, создаём Source с AUTO типом
            source = Source(source.split('/')[2] if '//' in source else source, source, SourceType.AUTO)

        return source.fetch(limit)

    @staticmethod
    def parse_multiple(sources: List[Union[Source, str]], limit_per_source: int = 5) -> List[Dict[str, Optional[str]]]:
        all_news = []

        for src in sources:
            news = UniversalParser.parse(src, limit_per_source)
            all_news.extend(news)

        return all_news


# Тестирование
if __name__ == "__main__":
    print("Тестирование мульти-источника")

    # 1. Тестируем SourceManager
    print("\n1. Тестируем SourceManager с предопределёнными источниками")

    manager = SourceManager(DEFAULT_SOURCES[:3])  # Берём первые 3 для теста
    manager.list_sources()

    # 2. Получаем новости
    print("\n2. Получаем новости из всех источников")

    all_news = manager.fetch_all(limit_per_source=3)

    print(f"\nВсего собрано новостей: {len(all_news)}")

    # Выводим первые 5 новостей
    print("\nПервые 5 новостей:")
    for i, item in enumerate(all_news[:5], 1):
        print(f"\n{i}. {item['title']}")
        print(f"Ссылка: {item['link']}")
        if item.get('published'):
            print(f"Дата публикации: {item['published']}")
        if item.get('summary'):
            summary = item['summary'][:100]
            print(f"Описание: {summary}...")

    #3. Тестируем UniversalParser
    print("\n3. Тестируем UniversalParser (автоопределение типа)")

    test_urls = [
        "https://lenta.ru/rss/news",           # RSS
        "https://ria.ru/lenta/",               # HTML
        "https://www.rbc.ru",                  # HTML
        "https://habr.com/ru/rss/all/",        # RSS
    ]

    for url in test_urls:
        print(f"\nПарсим: {url}")

        news = UniversalParser.parse(url, limit=2)

        for item in news:
            print(f"{item['title'][:80]}...")
            print(f"Ссылка: {item['link']}")

    # 4. Тестируем добавление/удаление источников
    print("\n4. Тестируем управление источниками")

    manager = SourceManager()
    manager.add_source(Source("Тестовый RSS", "https://lenta.ru/rss/news", SourceType.RSS))
    manager.add_source(Source("Тестовый HTML", "https://ria.ru/lenta/", SourceType.HTML))

    manager.list_sources()

    # Отключаем один источник
    manager.enable_source("Тестовый RSS", enabled=False)

    manager.list_sources()

    # Получаем новости только из включённых
    news = manager.fetch_all(limit_per_source=2)
    print(f"\nНовостей после отключения RSS: {len(news)}")
