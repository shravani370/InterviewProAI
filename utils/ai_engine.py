"""
utils/ai_engine.py — AI Engine (backward-compatible wrapper)
Now uses multi-backend abstraction layer (OpenAI, Anthropic, Gemini, Ollama)
"""
import os
import json
import logging
from utils.ai_backends import get_ai_manager

logger = logging.getLogger(__name__)


def generate_question(
    topic: str,
    previous_answer: str = "",
    history: list = None,
    asked_questions: list = None,
) -> str:
    """Generate an interview question using AI backend"""
    ai = get_ai_manager()
    asked_str = "\n".join(asked_questions or [])
    
    # Format history: convert dicts to strings
    if history:
        history_items = []
        for item in history:
            if isinstance(item, dict):
                role = item.get("role", "")
                text = item.get("text", "")
                history_items.append(f"{role}: {text}")
            else:
                history_items.append(str(item))
        history_str = "\n".join(history_items)
    else:
        history_str = ""
    
    prompt = f"""You are a senior technical interviewer specialising in {topic} (as of 2026).
Focus on LATEST industry practices, modern frameworks, and current best practices.
Generate ONE concise, relevant interview question that tests current knowledge.

Do NOT repeat any question from this list:
{asked_str}

Previous conversation:
{history_str}

Candidate's last answer: {previous_answer}

Return ONLY the question text."""
    return ai.generate(prompt)


def evaluate_answer(question: str, answer: str) -> dict:
    """Evaluate answer using AI backend"""
    ai = get_ai_manager()
    return ai.evaluate(question, answer)


def generate_mcq_questions(role: str, n: int = 10) -> list:
    """Generate MCQ questions for a given role using AI."""
    ai = get_ai_manager()
    prompt = f"""You are a technical recruiter creating {n} multiple-choice screening questions for a {role} position in 2026.
Use LATEST industry standards, best practices, and current technologies. Focus on modern approaches and frameworks.

Generate EXACTLY {n} questions in valid JSON array format. Each question MUST have these exact fields:
- "q": the question text (string)
- "options": exactly 4 answer options (array of strings) - list CORRECT answer FIRST
- "answer": the index 0-3 of the correct answer (integer) - make sure it points to the LATEST CORRECT answer

IMPORTANT: The correct answer should reflect CURRENT best practices (2026), not outdated information.

Example format:
[
  {{"q": "Question 1?", "options": ["opt1_CORRECT", "opt2_old", "opt3", "opt4"], "answer": 0}},
  {{"q": "Question 2?", "options": ["opt1_CORRECT", "opt2", "opt3_old", "opt4"], "answer": 0}}
]

Return ONLY the JSON array, no markdown, no text before or after."""
    
    raw = ai.generate(prompt)
    try:
        # Try to extract JSON from the response
        clean = raw.strip()
        
        # Remove markdown code blocks if present
        if "```" in clean:
            parts = clean.split("```")
            for part in parts:
                if part.strip().startswith("["):
                    clean = part.strip()
                    break
        
        # Remove leading/trailing whitespace and markers
        if clean.startswith("json"):
            clean = clean[4:].strip()
        if clean.startswith("["):
            # Find the first [ and last ]
            start = clean.find("[")
            end = clean.rfind("]")
            if start >= 0 and end > start:
                clean = clean[start:end+1]
        
        questions = json.loads(clean)
        
        # Validate structure
        validated = []
        for q in questions:
            if isinstance(q, dict):
                # Try to get required fields
                q_text = q.get("q") or q.get("question")
                options = q.get("options")
                answer = q.get("answer")
                
                if q_text and options and answer is not None:
                    if isinstance(options, list) and len(options) == 4:
                        if isinstance(answer, int) and 0 <= answer < 4:
                            validated.append({
                                "q": q_text,
                                "options": options,
                                "answer": answer
                            })
        
        # Return validated questions
        if validated:
            return validated[:n]
        
        logger.warning(f"MCQ validation failed for {role}, got {len(questions)} questions but none validated")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"MCQ JSON decode error for {role}: {e}\nRaw response: {raw[:200]}")
        return []
    except Exception as e:
        logger.error(f"MCQ generation error for {role}: {e}")
        return []


def generate_coding_questions(role: str, n: int = 2) -> list:
    """Generate coding challenge questions for a given role using AI."""
    ai = get_ai_manager()
    prompt = f"""You are a technical interviewer creating {n} coding challenges for a {role} position in 2026.
Use LATEST technologies, frameworks, and best practices. Focus on real-world relevance and modern approaches.

Generate EXACTLY {n} challenges in valid JSON array format. Each challenge MUST have:
- "id": unique identifier (string, snake_case)
- "func": function name to implement (string)
- "title": challenge title (string)
- "difficulty": "Easy" or "Medium" (string)
- "description": problem description with example using LATEST practices (string, can include newlines)
- "starter": Python function stub starting with def (string)
- "test_cases": array of objects with "input" (tuple) and "expected" (expected result)

Example:
[
  {{
    "id": "two_sum",
    "func": "two_sum",
    "title": "Two Sum Problem",
    "difficulty": "Easy",
    "description": "Find two numbers that add to target.",
    "starter": "def two_sum(nums, target):\\n    pass",
    "test_cases": [
      {{"input": ([1, 2, 3], 5), "expected": [1, 2]}},
      {{"input": ([1, 2], 3), "expected": [0, 1]}}
    ]
  }}
]

Return ONLY the JSON array, no markdown, no explanation."""
    
    raw = ai.generate(prompt)
    try:
        # Try to extract JSON from the response
        clean = raw.strip()
        
        # Remove markdown code blocks if present
        if "```" in clean:
            parts = clean.split("```")
            for part in parts:
                if part.strip().startswith("["):
                    clean = part.strip()
                    break
        
        # Remove leading markers
        if clean.startswith("json"):
            clean = clean[4:].strip()
        
        if clean.startswith("["):
            # Find the first [ and last ]
            start = clean.find("[")
            end = clean.rfind("]")
            if start >= 0 and end > start:
                clean = clean[start:end+1]
        
        questions = json.loads(clean)
        
        # Validate structure
        validated = []
        for q in questions:
            if isinstance(q, dict):
                required_fields = ["id", "func", "title", "difficulty", "description", "starter", "test_cases"]
                if all(field in q for field in required_fields):
                    if isinstance(q.get("test_cases"), list) and len(q["test_cases"]) >= 2:
                        validated.append({
                            "id": str(q["id"]),
                            "func": str(q["func"]),
                            "title": str(q["title"]),
                            "difficulty": str(q["difficulty"]),
                            "description": str(q["description"]),
                            "starter": str(q["starter"]),
                            "test_cases": q["test_cases"]
                        })
        
        # Return validated questions
        if validated:
            return validated[:n]
        
        logger.warning(f"Coding validation failed for {role}, got {len(questions)} questions but none validated")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Coding JSON decode error for {role}: {e}\nRaw response: {raw[:200]}")
        return []
    except Exception as e:
        logger.error(f"Coding generation error for {role}: {e}")
        return []