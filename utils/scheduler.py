import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional
from croniter import croniter


class TaskScheduler:
    """定时任务调度器"""

    def __init__(self):
        self._running = False
        self._thread = None
        self._tasks = []

    def add_task(self, name: str, schedule, callback: Callable):
        """添加定时任务"""
        self._tasks.append({
            "name": name,
            "schedule": schedule,
            "callback": callback,
            "last_run": None
        })

    def start(self):
        """启动调度器"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def remove_task(self, name: str):
        """移除任务"""
        self._tasks = [t for t in self._tasks if t["name"] != name]

    def _run(self):
        """调度循环"""
        while self._running:
            now = datetime.now()
            for task in self._tasks:
                try:
                    if self._should_run(now, task):
                        task["callback"]()
                        task["last_run"] = now
                except Exception as e:
                    print(f"定时任务执行失败 {task['name']}: {e}")
            time.sleep(30)  # 每30秒检查一次

    def _should_run(self, now: datetime, task) -> bool:
        """判断是否应该执行"""
        schedule = task["schedule"]
        if not schedule.enabled:
            return False

        schedule_type = schedule.schedule_type

        if schedule_type == "once":
            # 单次任务：检查是否到了设定时间
            # 简化处理：只在应用启动时检查一次
            if task["last_run"] is None:
                return True
            return False

        elif schedule_type == "daily":
            # 每日任务：检查当前时间是否等于设定时间
            target_time = schedule.daily_time
            current_time = now.strftime("%H:%M")
            if current_time == target_time:
                if task["last_run"] is None or task["last_run"].date() < now.date():
                    return True
            return False

        elif schedule_type == "weekly":
            # 每周任务：检查星期几和时间
            target_day = schedule.weekly_day
            target_time = schedule.weekly_time
            current_day = now.weekday()  # 0=Monday
            current_time = now.strftime("%H:%M")
            if current_day == target_day and current_time == target_time:
                if task["last_run"] is None or (now - task["last_run"]).days >= 7:
                    return True
            return False

        elif schedule_type == "cron":
            # Cron表达式
            try:
                cron = croniter(schedule.cron_expression, now)
                next_run = cron.get_next(datetime)
                # 如果当前时间接近下次执行时间（1分钟内），且距离上次执行足够远
                if task["last_run"] is None or (now - task["last_run"]).total_seconds() >= 60:
                    if abs((next_run - now).total_seconds()) < 60:
                        return True
            except Exception:
                pass
            return False

        return False

    def get_next_run_time(self, schedule) -> Optional[str]:
        """获取下次执行时间"""
        if not schedule.enabled:
            return None

        try:
            if schedule.schedule_type == "daily":
                now = datetime.now()
                target_hour, target_min = map(int, schedule.daily_time.split(":"))
                next_run = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run.strftime("%Y-%m-%d %H:%M")

            elif schedule.schedule_type == "weekly":
                now = datetime.now()
                target_hour, target_min = map(int, schedule.weekly_time.split(":"))
                days_ahead = schedule.weekly_day - now.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                elif days_ahead == 0:
                    target_time = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
                    if target_time <= now:
                        days_ahead = 7
                next_run = now + timedelta(days=days_ahead)
                next_run = next_run.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
                return next_run.strftime("%Y-%m-%d %H:%M")

            elif schedule.schedule_type == "cron":
                cron = croniter(schedule.cron_expression, datetime.now())
                next_run = cron.get_next(datetime)
                return next_run.strftime("%Y-%m-%d %H:%M")

        except Exception:
            pass

        return None
