"""Conversational query rewriting and self-evaluation helpers."""
import json
from typing import Any, Dict, List

from .prompts import build_condense_question_prompt, build_query_rewrite_prompt, build_self_eval_prompt
from .text import format_history


class RAGSelfRAGMixin:
    def _rewrite_query_for_retrieval(self, question: str, history: List[Dict[str, str]]) -> str:
        history_text = format_history(
            history,
            history_max_messages=self.history_max_messages,
            history_max_chars=self.history_max_chars,
        )
        prompt = build_query_rewrite_prompt(history_text=history_text, question=question)
        try:
            rewritten = self._invoke_llm(prompt).strip().strip('"')
            return rewritten or question
        except Exception:
            return question

    def _self_evaluate_answer(self, question: str, answer: str, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        context_preview = "\\n\\n".join([item.get("content", "")[:600] for item in contexts[:3]])
        prompt = build_self_eval_prompt(question=question, answer=answer, context_preview=context_preview)
        try:
            raw = self._invoke_llm(prompt)
            parsed = json.loads(raw)
            supported = bool(parsed.get("supported", False))
            confidence = float(parsed.get("confidence", 0.0))
            feedback = str(parsed.get("feedback", "")).strip()
            confidence = min(1.0, max(0.0, confidence))
            return {"supported": supported, "confidence": confidence, "feedback": feedback}
        except Exception:
            return {"supported": True, "confidence": 0.55, "feedback": "fallback"}

    @staticmethod
    def _confidence_label(score: float) -> str:
        if score >= 0.75:
            return "high"
        if score >= 0.45:
            return "medium"
        return "low"

    def _condense_question(self, history: List[Dict[str, str]], question: str) -> str:
        if not history:
            return question

        history_text = format_history(
            history,
            history_max_messages=self.history_max_messages,
            history_max_chars=self.history_max_chars,
        )

        condense_prompt = build_condense_question_prompt(history_text=history_text, question=question)

        try:
            condensed = self._invoke_llm(condense_prompt)
            condensed = str(condensed).strip().strip('"')
            return condensed or question
        except Exception:
            return question
