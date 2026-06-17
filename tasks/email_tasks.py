"""
Async tasks for email notifications
"""
from celery import shared_task
from celery.utils.log import get_task_logger
import os
from dotenv import load_dotenv

load_dotenv()

logger = get_task_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# EMAIL TASKS
# ═══════════════════════════════════════════════════════════════════════════

@shared_task(bind=True, max_retries=3)
def send_screening_results_email(self, user_email: str, role: str, mcq_score: int, code_score: int, passed: bool):
    """
    Send screening results email to user
    
    Args:
        user_email: User's email address
        role: Job role tested
        mcq_score: MCQ score (0-100)
        code_score: Coding score (0-100)
        passed: Whether user passed
    """
    try:
        from flask_mail import Message
        from app import mail
        
        logger.info(f"Sending screening results email to {user_email}")
        
        avg_score = (mcq_score + code_score) / 2
        status = "✅ PASSED" if passed else "❌ FAILED"
        
        msg = Message(
            subject=f"Your {role} Screening Results - {status}",
            recipients=[user_email],
            html=f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2>Your Interview Screening Results</h2>
                    <p><strong>Role:</strong> {role}</p>
                    <p><strong>MCQ Score:</strong> {mcq_score}/100</p>
                    <p><strong>Coding Score:</strong> {code_score}/100</p>
                    <p><strong>Average:</strong> {avg_score:.1f}/100</p>
                    <p><strong>Status:</strong> <span style="color: {'green' if passed else 'red'};">{status}</span></p>
                    <hr>
                    <p>Next steps:</p>
                    <ul>
                        <li><a href="https://interview-proai.com/dashboard">View detailed results</a></li>
                        <li>Practice more questions</li>
                        <li>Improve weak areas</li>
                    </ul>
                </body>
            </html>
            """
        )
        
        mail.send(msg)
        logger.info(f"✅ Email sent to {user_email}")
        return {"status": "sent", "email": user_email}
        
    except Exception as exc:
        logger.error(f"❌ Email send failed: {exc}")
        raise self.retry(exc=exc, countdown=300)  # Retry in 5 minutes


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self, user_email: str, reset_token: str):
    """
    Send password reset link to user
    """
    try:
        from flask_mail import Message
        from app import mail
        
        logger.info(f"Sending password reset email to {user_email}")
        
        reset_url = f"https://interview-proai.com/reset-password/{reset_token}"
        
        msg = Message(
            subject="Password Reset Request",
            recipients=[user_email],
            html=f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2>Password Reset</h2>
                    <p>Click the link below to reset your password:</p>
                    <p><a href="{reset_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none;">Reset Password</a></p>
                    <p>This link expires in 24 hours.</p>
                    <p>If you didn't request this, ignore this email.</p>
                </body>
            </html>
            """
        )
        
        mail.send(msg)
        logger.info(f"✅ Password reset email sent to {user_email}")
        return {"status": "sent", "email": user_email}
        
    except Exception as exc:
        logger.error(f"❌ Email send failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task
def send_job_alert_email(user_email: str, job_title: str, company: str):
    """
    Send job alert email for saved searches
    """
    try:
        from flask_mail import Message
        from app import mail
        
        logger.info(f"Sending job alert to {user_email} for {job_title}")
        
        msg = Message(
            subject=f"New {job_title} opportunity at {company}",
            recipients=[user_email],
            html=f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2>New Job Match!</h2>
                    <p><strong>Title:</strong> {job_title}</p>
                    <p><strong>Company:</strong> {company}</p>
                    <p><a href="https://interview-proai.com/jobs">View this opportunity</a></p>
                </body>
            </html>
            """
        )
        
        mail.send(msg)
        logger.info(f"✅ Job alert sent to {user_email}")
        
    except Exception as exc:
        logger.error(f"❌ Job alert send failed: {exc}")
