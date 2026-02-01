import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legal.settings')

app = Celery('legal')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send-task-reminders-every-day': {
        'task': 'crm.tasks.send_task_reminders',
        'schedule': crontab(hour=9, minute=0),  # Каждый день в 9:00
    },
    'generate-daily-analytics': {
        'task': 'crm.tasks.generate_daily_analytics',
        'schedule': crontab(hour=0, minute=30),  # Каждый день в 00:30
    },
    'cleanup-old-notifications': {
        'task': 'crm.tasks.cleanup_old_notifications',
        'schedule': crontab(day_of_month='1', hour=0, minute=0),  # 1-го числа каждого месяца
    },
}