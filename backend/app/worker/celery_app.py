"""
Celery Application — Background Job Processor.

Schedule edilen ve async görevler buradan yönetilir:
- Bütçe aşımı kontrolü (her gece)
- Fiyat takibi (saatlik)
- Email gönderimi (anlık)
"""

from __future__ import annotations
from app.core.config import settings
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "optiwallet",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        # TODO: task modüllerini ekle
        # "app.worker.tasks.budget_check",
        # "app.worker.tasks.price_tracker",
        # "app.worker.tasks.notifications",
    ],
)

# ===== Configuration =====
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Istanbul",
    enable_utc=True,
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=settings.REDIS_URL,
    redbeat_lock_timeout=90,
    redbeat_key_prefix="optiwallet:beat:",
    task_track_started=True,
    task_time_limit=300,  # 5 dakika
    task_soft_time_limit=240,  # 4 dakika
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=4,
)

# ===== Scheduled Tasks =====
celery_app.conf.beat_schedule = {
    # Her gece 03:00 — bütçe kontrolü
    "budget-check-nightly": {
        "task": "app.worker.tasks.budget_check.check_all_budgets",
        "schedule": crontab(hour=3, minute=0),
    },
    # Her saat — fiyat takibi
    "price-tracker-hourly": {
        "task": "app.worker.tasks.price_tracker.track_favorited_prices",
        "schedule": crontab(minute=0),
    },
    # Her sabah 09:00 — kupon süre uyarısı
    "coupon-expiry-warning": {
        "task": "app.worker.tasks.notifications.warn_expiring_coupons",
        "schedule": crontab(hour=9, minute=0),
    },
}


if __name__ == "__main__":
    celery_app.start()