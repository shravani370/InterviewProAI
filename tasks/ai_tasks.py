"""
Async tasks for AI generation
Replaces blocking OpenAI/Anthropic/Ollama calls
"""
from celery import shared_task
from celery.utils.log import get_task_logger
import os
from dotenv import load_dotenv

load_dotenv()

logger = get_task_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# QUESTION GENERATION TASK
# ═══════════════════════════════════════════════════════════════════════════

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_question_async(self, topic: str, previous_answer: str = "", history: list = None, asked_questions: list = None):
    """
    Async task: Generate interview question using AI
    
    Args:
        topic: Interview topic (e.g., "Python", "JavaScript")
        previous_answer: Candidate's last answer (for continuity)
        history: Conversation history
        asked_questions: Questions already asked
    
    Returns:
        dict: {"question": "...", "task_id": "...", "status": "success"}
    """
    try:
        from utils.ai_engine import generate_question
        
        logger.info(f"Generating question for topic: {topic}")
        
        question = generate_question(
            topic=topic,
            previous_answer=previous_answer or "",
            history=history or [],
            asked_questions=asked_questions or []
        )
        
        logger.info(f"✅ Question generated: {question[:50]}...")
        
        return {
            "question": question,
            "task_id": self.request.id,
            "status": "success"
        }
        
    except Exception as exc:
        logger.error(f"❌ Question generation failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def evaluate_answer_async(self, question: str, answer: str):
    """
    Async task: Evaluate candidate's answer
    
    Args:
        question: The interview question
        answer: Candidate's answer
    
    Returns:
        dict: {"score": 7, "strengths": "...", "improvements": "...", "verdict": "Good"}
    """
    try:
        from utils.ai_engine import evaluate_answer
        
        logger.info(f"Evaluating answer for question: {question[:50]}...")
        
        evaluation = evaluate_answer(question, answer)
        evaluation['task_id'] = self.request.id
        
        logger.info(f"✅ Answer evaluated, score: {evaluation.get('score', 'N/A')}/10")
        
        return evaluation
        
    except Exception as exc:
        logger.error(f"❌ Answer evaluation failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_mcq_questions_async(self, role: str, n: int = 10):
    """
    Async task: Generate MCQ questions for screening
    
    Args:
        role: Job role (e.g., "Senior Python Developer")
        n: Number of questions (default 10)
    
    Returns:
        dict: {"questions": [...], "task_id": "...", "status": "success"}
    """
    try:
        from utils.ai_engine import generate_mcq_questions
        
        logger.info(f"Generating {n} MCQ questions for role: {role}")
        
        questions = generate_mcq_questions(role, n)
        
        logger.info(f"✅ Generated {len(questions)} MCQ questions")
        
        return {
            "questions": questions,
            "task_id": self.request.id,
            "status": "success",
            "count": len(questions)
        }
        
    except Exception as exc:
        logger.error(f"❌ MCQ generation failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# ═══════════════════════════════════════════════════════════════════════════
# CHECK TASK STATUS
# ═══════════════════════════════════════════════════════════════════════════

@shared_task
def get_task_status(task_id: str):
    """Get status of an async task"""
    from celery_app import app
    result = app.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "state": result.state,
        "progress": 0,  # Can be extended with more granular progress
        "result": result.result if result.state == 'SUCCESS' else None,
        "error": str(result.info) if result.state == 'FAILURE' else None
    }
