"""
utils/ai_backends.py — Multi-backend AI abstraction layer
Supports: OpenAI, Anthropic, Google Gemini (primary for Render deployment)
"""
import os
import json
import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# BASE CLASS
# ═══════════════════════════════════════════════════════════════════════════

class AIBackend:
    def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError

    def evaluate(self, question: str, answer: str) -> Dict[str, Any]:
        raise NotImplementedError

    def health_check(self) -> bool:
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════════════
# JSON PARSING HELPER
# ═══════════════════════════════════════════════════════════════════════════

def _parse_json_response(raw: str, fallback: Dict) -> Dict:
    """Try multiple strategies to parse JSON from AI response."""
    for attempt in [
        lambda r: json.loads(r),
        lambda r: json.loads(r.strip().split("```")[1].lstrip("json").strip()) if "```" in r else None,
        lambda r: json.loads(r[r.index("{"):r.rindex("}") + 1]),
    ]:
        try:
            result = attempt(raw)
            if result:
                return result
        except Exception:
            pass
    logger.warning(f"JSON parse failed, using fallback. Raw: {raw[:200]}")
    return fallback


_EVAL_FALLBACK = {
    "score": 5,
    "strengths": "Answer provided",
    "improvements": "Could not evaluate — check AI configuration",
    "verdict": "Average",
    "feedback": "Thank you for your answer. Keep practising!",
}


# ═══════════════════════════════════════════════════════════════════════════
# GEMINI BACKEND  (primary for this deployment)
# ═══════════════════════════════════════════════════════════════════════════

class GeminiBackend(AIBackend):
    """Google Gemini API — set GOOGLE_GENAI_API_KEY in environment."""

    def __init__(self):
        # Support both common env-var names
        self.api_key = (
            os.environ.get("GOOGLE_GENAI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        self.model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
        if not self.api_key:
            logger.warning("GOOGLE_GENAI_API_KEY not set — Gemini unavailable")

    def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            model.generate_content("Say OK", stream=False)
            return True
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            return "[Gemini: GOOGLE_GENAI_API_KEY not set]"
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt, stream=False)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini generate error: {e}")
            return f"[Gemini error: {e}]"

    def evaluate(self, question: str, answer: str) -> Dict[str, Any]:
        prompt = f"""You are a senior technical interview evaluator (2026 best practices).

Question: {question}
Candidate answer: {answer}

Return ONLY valid JSON — no markdown, no extra text:
{{
  "score": <integer 1-10>,
  "strengths": "<one concise strength>",
  "improvements": "<one concrete improvement>",
  "verdict": "Excellent|Good|Average|Poor",
  "feedback": "<2-3 sentence conversational feedback to tell the candidate>"
}}"""
        raw = self.generate(prompt)
        result = _parse_json_response(raw, _EVAL_FALLBACK.copy())
        if "feedback" not in result:
            result["feedback"] = result.get("strengths", "Good attempt, keep practising.")
        return result


# ═══════════════════════════════════════════════════════════════════════════
# OPENAI BACKEND
# ═══════════════════════════════════════════════════════════════════════════

class OpenAIBackend(AIBackend):
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

    def health_check(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            return "[OpenAI: OPENAI_API_KEY not set]"
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.7),
                timeout=30,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI generate error: {e}")
            return f"[OpenAI error: {e}]"

    def evaluate(self, question: str, answer: str) -> Dict[str, Any]:
        prompt = f"""You are a senior technical interview evaluator (2026).

Question: {question}
Answer: {answer}

Return ONLY valid JSON:
{{
  "score": <integer 1-10>,
  "strengths": "<strength>",
  "improvements": "<improvement>",
  "verdict": "Excellent|Good|Average|Poor",
  "feedback": "<2-3 sentence conversational feedback>"
}}"""
        raw = self.generate(prompt, temperature=0)
        result = _parse_json_response(raw, _EVAL_FALLBACK.copy())
        if "feedback" not in result:
            result["feedback"] = result.get("strengths", "Good attempt!")
        return result


# ═══════════════════════════════════════════════════════════════════════════
# ANTHROPIC BACKEND
# ═══════════════════════════════════════════════════════════════════════════

class AnthropicBackend(AIBackend):
    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

    def health_check(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            return "[Anthropic: ANTHROPIC_API_KEY not set]"
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Anthropic generate error: {e}")
            return f"[Anthropic error: {e}]"

    def evaluate(self, question: str, answer: str) -> Dict[str, Any]:
        prompt = f"""You are a senior technical interview evaluator (2026).

Question: {question}
Answer: {answer}

Return ONLY valid JSON:
{{
  "score": <integer 1-10>,
  "strengths": "<strength>",
  "improvements": "<improvement>",
  "verdict": "Excellent|Good|Average|Poor",
  "feedback": "<2-3 sentence conversational feedback>"
}}"""
        raw = self.generate(prompt)
        result = _parse_json_response(raw, _EVAL_FALLBACK.copy())
        if "feedback" not in result:
            result["feedback"] = result.get("strengths", "Good attempt!")
        return result


# ═══════════════════════════════════════════════════════════════════════════
# OLLAMA BACKEND  (local only — not available on Render)
# ═══════════════════════════════════════════════════════════════════════════

class OllamaBackend(AIBackend):
    def __init__(self):
        self.url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.model = os.environ.get("OLLAMA_MODEL", "llama2")

    def health_check(self) -> bool:
        try:
            base = self.url.replace("/api/generate", "")
            resp = requests.get(f"{base}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str, **kwargs) -> str:
        try:
            resp = requests.post(
                self.url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama generate error: {e}")
            return f"[Ollama error: {e}]"

    def evaluate(self, question: str, answer: str) -> Dict[str, Any]:
        prompt = f"""Evaluate this interview answer. Return ONLY JSON:
Question: {question}
Answer: {answer}
{{"score":<1-10>,"strengths":"<str>","improvements":"<str>","verdict":"Good","feedback":"<str>"}}"""
        raw = self.generate(prompt)
        result = _parse_json_response(raw, _EVAL_FALLBACK.copy())
        if "feedback" not in result:
            result["feedback"] = result.get("strengths", "Good attempt!")
        return result


# ═══════════════════════════════════════════════════════════════════════════
# AI MANAGER — auto-selects best available backend
# ═══════════════════════════════════════════════════════════════════════════

class AIManager:
    # Priority order: Gemini first (our chosen backend for Render)
    _PRIORITY = ["gemini", "openai", "anthropic", "ollama"]

    def __init__(self):
        self._backends: Dict[str, AIBackend] = {
            "gemini":    GeminiBackend(),
            "openai":    OpenAIBackend(),
            "anthropic": AnthropicBackend(),
            "ollama":    OllamaBackend(),
        }
        self._active: Optional[AIBackend] = None
        self._active_name: str = "none"
        self._select()

    def _select(self):
        for name in self._PRIORITY:
            backend = self._backends[name]
            if backend.health_check():
                self._active = backend
                self._active_name = name
                logger.info(f"✅ AI backend selected: {name}")
                return
        # Soft fallback — Gemini even if health check failed
        # (network issues during startup shouldn't block the app)
        self._active = self._backends["gemini"]
        self._active_name = "gemini (fallback)"
        logger.warning("No AI backend passed health check — using Gemini as soft fallback")

    def generate(self, prompt: str, **kwargs) -> str:
        if not self._active:
            return "[No AI backend available]"
        return self._active.generate(prompt, **kwargs)

    def evaluate(self, question: str, answer: str) -> Dict[str, Any]:
        if not self._active:
            return _EVAL_FALLBACK.copy()
        return self._active.evaluate(question, answer)

    def status(self) -> Dict[str, Any]:
        return {
            "active": self._active_name,
            "backends": {
                name: backend.health_check()
                for name, backend in self._backends.items()
            },
        }


# ─── Singleton ───────────────────────────────────────────────────────────
_manager: Optional[AIManager] = None


def get_ai_manager() -> AIManager:
    global _manager
    if _manager is None:
        _manager = AIManager()
    return _manager