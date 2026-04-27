# qa_agent.py
# Умный QA-агент с нейросетевым ответом через OpenRouter
# Работает как полноценный LLM-ассистент

import os
import re
import logging
import time
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# РАБОЧИЕ БЕСПЛАТНЫЕ МОДЕЛИ (проверенные 26.04.2026)
FREE_MODELS = [
    "deepseek/deepseek-chat-v3-0324:free",  # DeepSeek V3 - отличная
    "deepseek/deepseek-r1:free",  # DeepSeek R1 - с рассуждениями
    "qwen/qwen-2.5-72b-instruct:free",  # Qwen 2.5 72B
    "mistralai/mistral-small-3.1-24b-instruct:free",  # Mistral Small
    "moonshotai/moonlight-16b-a3b-instruct:free",  # Moonlight 16B
    "nvidia/llama-3.1-nemotron-70b-instruct:free",  # Nemotron 70B
]

# Платные (если есть деньги на счету)
PAID_MODELS = [
    "openai/gpt-4o-mini",
    "anthropic/claude-3-haiku",
]

TEMPERATURE = 0.7
MAX_TOKENS = 800
TIMEOUT = 30


# ═══════════════════════════════════════════════════════════════
# ПОИСК В ИНТЕРНЕТЕ
# ═══════════════════════════════════════════════════════════════

def search_web(query: str, max_results: int = 5) -> List[Dict]:
    """Ищет через новый пакет ddgs"""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            logger.info(f"Найдено {len(results)} результатов")
            return results
    except ImportError:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return []


def _build_context(query: str) -> str:
    """Собирает контекст из поиска"""
    results = search_web(query, max_results=4)
    if not results:
        return ""

    parts = []
    for r in results:
        title = r.get("title", "")
        body = r.get("body", "")
        href = r.get("href", "")

        # Пропускаем мусор
        if any(b in href.lower() for b in ["otvet.mail.ru", "yandex.ru/q", "bolshoyvopros.ru"]):
            continue

        parts.append(f"Источник: {title}\n{body}\n")

    return "\n".join(parts[:3])[:3000]


# ═══════════════════════════════════════════════════════════════
# OpenRouter API
# ═══════════════════════════════════════════════════════════════

def _try_model(model: str, messages: List[Dict], api_key: str) -> Optional[str]:
    """Пробует одну модель"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/newsagent",
        "X-Title": "NewsAgent"
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )

        if resp.status_code == 200:
            data = resp.json()
            answer = data["choices"][0]["message"]["content"]
            logger.info(f"✅ Модель {model} ответила ({len(answer)} символов)")
            return answer.strip()
        else:
            error = resp.json().get("error", {}).get("message", str(resp.status_code))
            logger.warning(f"❌ {model}: {error}")
            return None

    except Exception as e:
        logger.warning(f"❌ {model}: {e}")
        return None


def ask_openrouter(question: str, context: str) -> str:
    """Отправляет вопрос к OpenRouter, перебирая модели"""
    if not OPENROUTER_API_KEY:
        return ""

    system_prompt = """Ты — полезный ассистент. Отвечай на русском языке.

Правила:
1. Отвечай развернуто, но по делу (3-6 предложений)
2. Если есть контекст из поиска — используй его
3. Структурируй ответ: сначала главное, потом детали
4. Будь дружелюбным
5. Не упоминай что ты ИИ или нейросеть"""

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    if context:
        messages.append({
            "role": "system",
            "content": f"Информация из интернета по запросу пользователя:\n{context}"
        })

    messages.append({"role": "user", "content": question})

    # Пробуем бесплатные модели
    for model in FREE_MODELS:
        answer = _try_model(model, messages, OPENROUTER_API_KEY)
        if answer:
            return answer

    # Пробуем платные
    for model in PAID_MODELS:
        answer = _try_model(model, messages, OPENROUTER_API_KEY)
        if answer:
            return answer

    return ""


# ═══════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════════

def ask_question(question: str, user_id: int = None) -> str:
    """
    Задает вопрос нейросети с поиском в интернете.
    """
    if not question or len(question.strip()) < 2:
        return "❌ Задайте вопрос подробнее."

    question = question.strip().strip('"').strip("'")
    logger.info(f"Вопрос: {question[:80]}...")

    # Ищем контекст
    context = _build_context(question)

    # Спрашиваем нейросеть
    answer = ask_openrouter(question, context)

    if answer:
        # Форматируем
        response = f"🤖 *{question[:60]}{'...' if len(question) > 60 else ''}*\n\n"
        response += answer
        response += f"\n\n⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        return response

    # Если все модели недоступны
    return (
        "❌ Сервис временно недоступен.\n\n"
        "Бесплатные модели OpenRouter сейчас перегружены.\n"
        "Попробуйте через несколько минут или проверьте API ключ.\n\n"
        "💡 Получить ключ: https://openrouter.ai/keys"
    )


# ═══════════════════════════════════════════════════════════════
# ТЕСТ
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТ QA-АГЕНТА")
    print("=" * 60)

    if not OPENROUTER_API_KEY:
        print("\n❌ Нет OPENROUTER_API_KEY в .env файле!")
        print("Добавь ключ из https://openrouter.ai/keys")
        print("Формат: OPENROUTER_API_KEY=sk-or-v1-твой-ключ\n")
    else:
        print(f"✅ Ключ найден: {OPENROUTER_API_KEY[:20]}...")

    tests = [
        "Что такое машинное обучение простыми словами?",
        "Сколько планет в Солнечной системе?",
        "В каком году основали КПРФ?",
    ]

    for q in tests:
        print(f"\n{'=' * 60}")
        print(f"ВОПРОС: {q}")
        print("=" * 60)
        answer = ask_question(q)
        print(f"\nОТВЕТ:\n{answer}\n")
        print("-" * 60)
