# scheduler.py
# Планировщик рассылок с поддержкой календаря

import asyncio
from datetime import datetime, time
from typing import List, Dict, Callable
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

class NewsScheduler:
    def __init__(self, bot, send_callback: Callable):
        self.bot = bot
        self.send_callback = send_callback
        self.scheduler = AsyncIOScheduler()
        self.user_schedules = {}  # user_id -> list of rules

    def add_schedule(self, user_id: int, rule: Dict):
        """
        Добавляет расписание для пользователя.
        rule = {
            'days': [0,1,2,3,4,5,6],  # 0=пн, 6=вс
            'hour': 7,
            'minute': 0,
            'enabled': True
        }
        """
        if user_id not in self.user_schedules:
            self.user_schedules[user_id] = []

        self.user_schedules[user_id].append(rule)

        # Создаём триггер для каждого правила
        trigger = CronTrigger(
            day_of_week=','.join(map(str, rule['days'])),
            hour=rule['hour'],
            minute=rule['minute']
        )
        job_id = f"{user_id}_{rule['hour']}_{rule['minute']}_{rule['days']}"

        self.scheduler.add_job(
            self._send_to_user,
            trigger,
            args=[user_id],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Добавлено расписание для {user_id}: {rule}")

    def remove_all_schedules(self, user_id: int):
        """Удаляет все расписания пользователя"""
        if user_id in self.user_schedules:
            del self.user_schedules[user_id]

        # Удаляем все джобы пользователя
        for job in self.scheduler.get_jobs():
            if job.id.startswith(str(user_id)):
                job.remove()
        logger.info(f"Удалены все расписания для {user_id}")

    async def _send_to_user(self, user_id: int):
        """Отправляет новости пользователю по расписанию"""
        logger.info(f"Отправка новостей пользователю {user_id} по расписанию")
        try:
            # Импортируем здесь, чтобы избежать циклических импортов
            from agent import run_agent
            news_text = run_agent(style="casual", for_telegram=True, limit_per_source=3)
            await self.bot.messages.send(user_id=user_id, message=news_text, random_id=0)
        except Exception as e:
            logger.error(f"Ошибка при отправке по расписанию {user_id}: {e}")

    def start(self):
        self.scheduler.start()
        logger.info("Планировщик запущен")

    def stop(self):
        self.scheduler.shutdown()