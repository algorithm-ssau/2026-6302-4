# summarizer.py
# Умный пересказ новостей с нейросетевым улучшением
# Использует OpenRouter API для качественного пересказа
# Если API недоступен - использует локальный экстрактивный метод

import re
import math
import os
import logging
import random
from collections import Counter
from typing import List
from dotenv import load_dotenv
import requests

load_dotenv()
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# OpenRouter API для пересказа
# ═══════════════════════════════════════════════════════════════

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Бесплатные модели для пересказа (быстрые и легкие)
SUMMARY_MODELS = [
    "deepseek/deepseek-chat-v3-0324:free",
    "deepseek/deepseek-r1:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "moonshotai/moonlight-16b-a3b-instruct:free",
    "nvidia/llama-3.1-nemotron-70b-instruct:free",
    "openai/gpt-4o-mini",
]


def _summarize_with_ai(text: str, style: str = "formal") -> str:
    """Пересказывает текст с помощью нейросети через OpenRouter"""
    if not OPENROUTER_API_KEY:
        logger.warning("OpenRouter API ключ не найден, использую локальный пересказ")
        return ""

    text_length = len(text)

    # Мягкая подсказка о желаемом объёме
    if style == "brief":
        length_hint = "Сделай короткий пересказ — только самую суть, 3-5 предложений."
    elif style == "detailed":
        if text_length < 500:
            length_hint = "Исходный текст короткий — передай его содержание полностью, но связно."
        elif text_length < 2000:
            length_hint = "Сделай развёрнутый пересказ, сохранив все ключевые детали."
        else:
            length_hint = "Исходный текст большой — сделай подробный пересказ, отразив все значимые факты, цифры и выводы."
    elif style == "casual":
        length_hint = "Перескажи простым языком, но с сохранением конкретных фактов и имён."
    else:
        length_hint = "Сделай сбалансированный деловой пересказ."

    style_prompts = {
        "formal": f"Ты — редактор новостей. {length_hint}",
        "casual": f"Ты — журналист, объясняющий новости простым языком. {length_hint}",
        "brief": f"Ты — редактор новостной ленты. Выдели САМУЮ СУТЬ. {length_hint}",
        "detailed": f"Ты — аналитик. {length_hint}"
    }

    style_instruction = style_prompts.get(style, style_prompts["formal"])

    system_prompt = f"""{style_instruction}

ЖЁСТКИЕ ПРАВИЛА ПЕРЕСКАЗА:
1. Ты работаешь ТОЛЬКО с текстом, который предоставил пользователь. Не додумывай факты.
2. Сохраняй ВСЕ конкретные имена (Песков, Путин, Байден...), названия (Кремль, Белый дом...), источники («Известия», Reuters...)
3. Если в тексте есть цитата — передай её суть своими словами, но сохрани смысл и контекст
4. Не пиши общими фразами вроде «это важное событие для международных отношений» — пиши КОНКРЕТНО, что произошло
5. Начинай сразу с сути: КТО, ЧТО, ГДЕ, КОГДА
6. Не используй «В тексте сообщается», «Автор пишет» — просто пересказывай факты"""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""Перескажи эту новость, следуя правилам. Сохрани все имена, цитаты и конкретные факты.

ТЕКСТ НОВОСТИ:
{text}

ПЕРЕСКАЗ:"""
        }
    ]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/newsagent",
        "X-Title": "NewsAgent Summarizer"
    }

    for model in SUMMARY_MODELS:
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.3,  # Ещё меньше креативности
                "max_tokens": 3000,
            }

            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )

            if resp.status_code == 200:
                data = resp.json()
                summary = data["choices"][0]["message"]["content"].strip()
                summary = summary.strip('"').strip("'").strip()

                # Проверка на галлюцинации: смотрим, есть ли конкретика
                # Если пересказ слишком общий и не содержит имён из оригинала — пробуем другую модель
                if len(summary) > 20:
                    logger.info(f"✅ Пересказ через {model} ({len(summary)} символов)")
                    return summary
                else:
                    logger.warning(f"   ⚠️ Модель {model} вернула слишком короткий пересказ ({len(summary)} символов)")
                    continue
                logger.info(f"✅ Пересказ через {model} ({len(summary)} символов, исходный: {text_length} символов)")
                return summary
            else:
                logger.warning(f"❌ Модель {model} недоступна: {resp.status_code}")

        except Exception as e:
            logger.warning(f"❌ Ошибка с моделью {model}: {e}")
            continue

    logger.warning("Все нейросетевые модели недоступны, использую локальный пересказ")
    return ""


class SmartSummarizer:
    """Умный пересказ: сначала пробует нейросеть, затем локальный метод"""

    IMPORTANCE_MARKERS = [
        'впервые', 'прорыв', 'революционный', 'уникальный', 'сенсация',
        'эксклюзив', 'объявил', 'анонсировал', 'представил', 'разработал',
        'создал', 'запустил', 'открыл', 'рекорд', 'достиг',
        'сообщил', 'рассказал', 'пояснил', 'отметил', 'подчеркнул',
        'новый', 'улучшенный', 'обновленный', 'исследование', 'показало',
        'оказалось', 'выяснилось', 'сообщается', 'заявил'
    ]

    def _split_sentences(self, text: str) -> List[str]:
        """Разбивка на предложения через регулярки - работает ВСЕГДА"""
        text = re.sub(r'\s+', ' ', text)
        sentences = re.split(r'(?<=[.!?;:])\s+(?=[A-ZА-Я"«])', text)

        if len(sentences) <= 1:
            sentences = re.split(r'(?<=[.!?])\s+', text)

        result = []
        for s in sentences:
            s = s.strip()
            if len(s) > 15:
                result.append(s)

        if not result:
            result = [text.strip()]

        return result

    def _clean_text(self, text: str) -> str:
        """Очистка текста от мусора"""
        if not text:
            return ""

        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'\S+@\S+', '', text)
        text = re.sub(r'(?i)(читать\s*также|подробнее|узнать\s*больше|реклама|спонсор).*$', '', text)
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _get_words(self, text: str) -> List[str]:
        """Получение списка слов из текста"""
        return re.findall(r'[а-яёa-z0-9]+', text.lower())

    def _score_sentence(self, sentence: str, position: int, total: int,
                        word_weights: dict, all_words_count: int) -> float:
        """Оценка важности одного предложения"""
        score = 0.0
        words = self._get_words(sentence)

        if not words:
            return 0

        for word in words:
            if word in word_weights:
                score += word_weights[word]

        score = score / len(words) * 10

        if position == 0:
            score += 25
        elif position == 1:
            score += 15
        elif position == 2:
            score += 10
        elif position <= total * 0.2:
            score += 8
        elif position >= total * 0.8:
            score += 6

        sent_lower = sentence.lower()
        for marker in self.IMPORTANCE_MARKERS[:13]:
            if marker in sent_lower:
                score += 12

        for marker in self.IMPORTANCE_MARKERS[13:]:
            if marker in sent_lower:
                score += 6

        if re.search(r'\d+', sentence):
            score += min(len(re.findall(r'\d+', sentence)) * 3, 10)

        if '"' in sentence or '«' in sentence or '»' in sentence:
            score += 8

        length = len(sentence)
        if 30 <= length <= 200:
            score += 3
        elif length < 20:
            score -= 2
        elif length > 300:
            score -= 1

        return score

    def _extractive_summary(self, sentences: List[str], max_length: int = 10000) -> str:
        """Экстрактивный пересказ (выбор важных предложений) - БЕЗ ЖЕСТКОЙ ОБРЕЗКИ"""
        if not sentences:
            return ""

        if len(sentences) == 1:
            return sentences[0]

        total_text = ' '.join(sentences)
        if len(total_text) <= max_length:
            return total_text

        all_words = []
        for sent in sentences:
            all_words.extend(self._get_words(sent))

        word_freq = Counter(all_words)
        total_sentences = len(sentences)

        word_weights = {}
        for word, freq in word_freq.items():
            doc_count = sum(1 for sent in sentences if word in self._get_words(sent))
            idf = math.log(total_sentences / (1 + doc_count))
            word_weights[word] = freq * idf

        scored = []
        for i, sent in enumerate(sentences):
            s = self._score_sentence(sent, i, total_sentences, word_weights, len(all_words))
            scored.append((sent, s, i))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Берем до 70% предложений, но не все
        target_count = max(4, min(len(sentences) // 2, int(len(sentences) * 0.7)))

        selected = []
        for sent, score, orig_idx in scored[:target_count]:
            selected.append((sent, orig_idx))

        selected.sort(key=lambda x: x[1])
        result = '. '.join(s[0] for s in selected)
        result = re.sub(r'\.{2,}', '.', result)

        if result and not result.endswith(('.', '!', '?')):
            result += '.'

        return result

    def _casual_extractive(self, sentences: List[str], max_length: int = 10000) -> str:
        """Неформальный экстрактивный пересказ"""
        formal = self._extractive_summary(sentences, max_length)

        if not formal:
            return "Пока новостей нет."

        starters = ["Короче, ", "Если кратко, то ", "В общем, ", "Смотри: "]
        starter = random.choice(starters)

        result = starter + formal[0].lower() + formal[1:]

        replacements = {
            'сообщается': 'говорят',
            'заявил': 'сказал',
            'разработали': 'сделали',
            'осуществили': 'провели',
            'представили': 'показали',
            'сообщил': 'рассказал',
            'отметил': 'добавил'
        }

        for old, new in replacements.items():
            result = re.sub(r'\b' + old + r'\b', new, result, flags=re.IGNORECASE)

        return result

    def _brief_extractive(self, sentences: List[str], max_length: int = 10000) -> str:
        """Очень краткий экстрактивный пересказ (3-4 предложения)"""
        if not sentences:
            return ""

        main = sentences[0]

        best_sentences = []
        best_scores = []

        for sent in sentences[1:]:
            score = 0
            sent_lower = sent.lower()

            for marker in self.IMPORTANCE_MARKERS[:13]:
                if marker in sent_lower:
                    score += 1

            if score > 0:
                best_sentences.append(sent)
                best_scores.append(score)

        if best_sentences:
            sorted_pairs = sorted(zip(best_sentences, best_scores), key=lambda x: x[1], reverse=True)
            top_additional = [pair[0] for pair in sorted_pairs[:2]]
            result = main + '. ' + '. '.join(top_additional)
        else:
            if len(sentences) > 2:
                mid = len(sentences) // 2
                result = main + '. ' + sentences[mid]
            else:
                result = main

        if result and not result.endswith(('.', '!', '?')):
            result += '.'

        return result

    def _detailed_extractive(self, sentences: List[str], max_length: int = 10000) -> str:
        """Подробный экстрактивный пересказ (сохраняет максимум деталей)"""
        if not sentences:
            return ""

        total_text = ' '.join(sentences)
        if len(total_text) <= max_length:
            return total_text

        # Берем до 80% предложений для подробного пересказа
        target_count = max(5, int(len(sentences) * 0.8))

        # Оцениваем важность
        all_words = []
        for sent in sentences:
            all_words.extend(self._get_words(sent))

        word_freq = Counter(all_words)
        total_sentences = len(sentences)

        word_weights = {}
        for word, freq in word_freq.items():
            doc_count = sum(1 for sent in sentences if word in self._get_words(sent))
            idf = math.log(total_sentences / (1 + doc_count))
            word_weights[word] = freq * idf

        scored = []
        for i, sent in enumerate(sentences):
            s = self._score_sentence(sent, i, total_sentences, word_weights, len(all_words))
            scored.append((sent, s, i))

        scored.sort(key=lambda x: x[1], reverse=True)
        selected = [(sent, idx) for sent, score, idx in scored[:target_count]]
        selected.sort(key=lambda x: x[1])

        result = '. '.join(s[0] for s in selected)
        result = re.sub(r'\.{2,}', '.', result)

        if result and not result.endswith(('.', '!', '?')):
            result += '.'

        return result

    def summarize(self, text: str, style: str = "formal") -> str:
        """
        Главный метод пересказа.
        Сначала пробует нейросеть, если не получается - использует экстрактивный метод.
        НЕ ОБРЕЗАЕТ результат!
        """
        if not text:
            return ""

        cleaned = self._clean_text(text)

        if not cleaned or len(cleaned) < 30:
            return cleaned

        # ПРОБУЕМ НЕЙРОСЕТЕВОЙ ПЕРЕСКАЗ (без обрезки)
        ai_summary = _summarize_with_ai(cleaned, style)
        if ai_summary:
            return ai_summary

        # ЛОКАЛЬНЫЙ МЕТОД - без жесткой обрезки
        logger.info("Использую локальный экстрактивный пересказ")
        sentences = self._split_sentences(cleaned)

        if not sentences:
            return cleaned

        if style == "casual":
            return self._casual_extractive(sentences)
        elif style == "brief":
            return self._brief_extractive(sentences)
        elif style == "detailed":
            return self._detailed_extractive(sentences)
        else:  # formal
            return self._extractive_summary(sentences)


# Создаем один экземпляр для всего проекта
_summarizer = SmartSummarizer()


def summarize_text(text: str, style: str = "formal") -> str:
    """
    Функция для вызова из других модулей.
    style: formal, casual, brief, detailed
    НЕ ОБРЕЗАЕТ результат по длине!
    """
    if not text or len(text.strip()) < 10:
        return text if text else ""

    result = _summarizer.summarize(text, style)

    # Если результат пустой или что-то пошло не так
    if not result:
        return text[:500] if len(text) > 500 else text

    return result


# Для совместимости с agent.py
generate_summary = summarize_text


# Тесты
if __name__ == "__main__":
    test_news = [
        "Пиво — это слабоалкогольный напиток (обычно 3–12% спирта), получаемый путем брожения солодового сусла с использованием пивных дрожжей. Основные ингредиенты: вода (90–95%), ячменный солод (пророщенные и высушенные зерна ячменя, которые дают сахара и цвет), хмель (добавляет горечь, аромат и служит консервантом) и дрожжи (превращают сахара в спирт и углекислый газ). Процесс варки включает затирание (смешивание солода с горячей водой для расщепления крахмалов в сахара), фильтрацию затора (отделение жидкого сусла от дробины), кипячение с хмелем (для стерилизации и извлечения горечи), охлаждение и аэрацию, ферментацию (брожение — от нескольких дней до недель), дозревание (лагерование при низких температурах), фильтрацию (по желанию), карбонизацию (насыщение CO₂) и розлив. По типу брожения пиво делится на лагеры (низовое брожение при 7–13°C, чистое и гладкое — например, Pilsner, Helles, Bock), эли (верховое брожение при 15–24°C, с фруктовыми и сложными ароматами — Pale Ale, IPA, Stout, Porter, Witbier) и спонтанное брожение (дикие дрожжи из воздуха, например, ламбик). Популярные стили: Pilsner (светлый лагер с хмелевой горечью), IPA (India Pale Ale — эль с высокой хмелевой горечью и ароматом), Stout (темный эль с нотками кофе и шоколада, как Гиннесс), Porter (темный, менее обжаренный), пшеничное (с нотами банана и гвоздики) и кислое (Gose, Berliner Weisse, Lambic). Краткая история: пиво известно с древности (6000 лет до н.э. у шумеров); в Средние века монастыри совершенствовали технологию; в 1516 году в Баварии принят закон Reinheitsgebot (чистота пива — только вода, солод, хмель, позже добавили дрожжи); в XIX веке Луи Пастер открыл роль дрожжей, появились лагеры и промышленное производство; в конце XX века началась крафтовая революция. Пиво различают по цвету (светлое, янтарное, коричневое, темное, черное) и по крепости (безалкогольное <0,5%, легкое 0,5–3%, традиционное 3–6%, крепкое 6–12%, барливайн >12%). По температуре подачи: лагеры 3–7°C, эли и стауты 8–12°C, бочковые и крепкие эли 12–14°C. Бокалы используются разные: пинта для элей, тюльпан для IPA, снифтер для крепких, вейцен для пшеничного, шопен для лагеров. Умеренное потребление (1-2 бокала в день для мужчин, 1 для женщин) может потенциально повышать хороший холестерин и давать антиоксиданты, но риски включают похмелье, зависимость, калорийность (пивной живот), повышение давления и взаимодействие с лекарствами. ВОЗ считает самой безопасной нулевую дозу."
    ]

    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ПЕРЕСКАЗА (БЕЗ ОБРЕЗКИ)")
    print("=" * 60)

    if OPENROUTER_API_KEY:
        print(f"✅ OpenRouter API ключ найден: {OPENROUTER_API_KEY[:20]}...")
    else:
        print("❌ OpenRouter API ключ не найден (будет использован локальный пересказ)")

    for i, news in enumerate(test_news, 1):
        print(f"\n📰 Новость {i} ({len(news)} символов)")
        print("-" * 40)

        print("\n📝 Пересказы:")

        for style in ["formal", "casual", "brief", "detailed"]:
            print(f"\n  [{style.upper()}]")
            summary = summarize_text(news, style=style)
            print(f"  {summary}")
            print(f"  (Длина: {len(summary)} символов)")

        print("\n" + "-" * 60)

    print("\n✅ ТЕСТЫ ЗАВЕРШЕНЫ!")