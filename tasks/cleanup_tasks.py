"""
Cleanup and maintenance tasks
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
import os

logger = get_task_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CLEANUP TASKS
# ═══════════════════════════════════════════════════════════════════════════

@shared_task
def cleanup_sessions():
    """
    Periodic task: Clean up expired sessions
    Runs daily at 2 AM
    """
    try:
        from models.db import db
        
        logger.info("🧹 Cleaning up expired sessions...")
        
        # Sessions are stored in Redis, so no DB cleanup needed
        # This is a placeholder for future improvements
        
        logger.info("✅ Session cleanup complete")
        return {"status": "success", "cleaned": 0}
        
    except Exception as exc:
        logger.error(f"❌ Session cleanup failed: {exc}")
        return {"status": "failed", "error": str(exc)}


@shared_task
def cleanup_cache():
    """
    Periodic task: Clean up old cached AI responses
    Runs daily at 3 AM
    """
    try:
        import redis
        from app import app
        
        logger.info("🧹 Cleaning up old cache entries...")
        
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        
        # Get all keys matching pattern
        pattern = "ai:question:*"
        old_time = datetime.utcnow() - timedelta(days=7)
        
        cursor = 0
        deleted = 0
        
        while True:
            cursor, keys = r.scan(cursor, match=pattern, count=100)
            for key in keys:
                ttl = r.ttl(key)
                if ttl > 0:  # Skip keys without expiry
                    continue
                r.delete(key)
                deleted += 1
            
            if cursor == 0:
                break
        
        logger.info(f"✅ Cache cleanup complete, deleted {deleted} entries")
        return {"status": "success", "deleted": deleted}
        
    except Exception as exc:
        logger.error(f"❌ Cache cleanup failed: {exc}")
        return {"status": "failed", "error": str(exc)}


@shared_task
def cleanup_uploads():
    """
    Periodic task: Clean up old uploaded files
    Deletes uploads older than 30 days
    """
    try:
        import os
        import glob
        from datetime import datetime, timedelta
        
        logger.info("🧹 Cleaning up old uploads...")
        
        uploads_dir = "./uploads"
        if not os.path.exists(uploads_dir):
            return {"status": "success", "cleaned": 0}
        
        cutoff_time = datetime.now() - timedelta(days=30)
        deleted = 0
        
        for file_path in glob.glob(os.path.join(uploads_dir, "*")):
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_time:
                    os.remove(file_path)
                    deleted += 1
        
        logger.info(f"✅ Upload cleanup complete, deleted {deleted} files")
        return {"status": "success", "cleaned": deleted}
        
    except Exception as exc:
        logger.error(f"❌ Upload cleanup failed: {exc}")
        return {"status": "failed", "error": str(exc)}


@shared_task
def generate_daily_report():
    """
    Periodic task: Generate daily analytics report
    Runs daily at 6 AM
    """
    try:
        from models.db import db, User, ScreeningResult
        from sqlalchemy import func
        
        logger.info("📊 Generating daily report...")
        
        # Get today's statistics
        today = datetime.now().date()
        
        new_users = db.session.query(User).filter(
            func.date(User.created_at) == today
        ).count()
        
        today_screenings = db.session.query(ScreeningResult).filter(
            func.date(ScreeningResult.created_at) == today
        ).count()
        
        passed_today = db.session.query(ScreeningResult).filter(
            func.date(ScreeningResult.created_at) == today,
            ScreeningResult.passed == 1
        ).count()
        
        report = {
            "date": str(today),
            "new_users": new_users,
            "screenings": today_screenings,
            "passed": passed_today,
            "pass_rate": (passed_today / today_screenings * 100) if today_screenings > 0 else 0
        }
        
        logger.info(f"✅ Daily report: {report}")
        return report
        
    except Exception as exc:
        logger.error(f"❌ Report generation failed: {exc}")
        return {"status": "failed", "error": str(exc)}
