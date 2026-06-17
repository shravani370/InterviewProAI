"""
Celery application setup for async tasks
Tasks include: AI generation, resume parsing, email sending, etc.
"""
import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

# Configure Celery
app = Celery('interview_proai')

# Broker URL (Redis)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

app.conf.update(
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,
    
    # Task configuration
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # Hard timeout: 30 minutes
    task_soft_time_limit=25 * 60,  # Soft timeout: 25 minutes
    
    # Worker configuration
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results to Redis
    
    # Routing
    task_routes={
        'tasks.ai_tasks.*': {'queue': 'ai'},
        'tasks.email_tasks.*': {'queue': 'email'},
        'tasks.resume_tasks.*': {'queue': 'resume'},
    },
)

# ═══════════════════════════════════════════════════════════════════════════
# CELERY BEAT SCHEDULE (Periodic Tasks)
# ═══════════════════════════════════════════════════════════════════════════
app.conf.beat_schedule = {
    'cleanup-expired-sessions': {
        'task': 'tasks.cleanup_tasks.cleanup_sessions',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'cleanup-old-cache': {
        'task': 'tasks.cleanup_tasks.cleanup_cache',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# AUTO-DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════
app.autodiscover_tasks(['tasks'])

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')
    return 'Celery is working! ✅'
