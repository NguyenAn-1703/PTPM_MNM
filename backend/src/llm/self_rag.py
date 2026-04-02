"""Conversational query rewriting and self-evaluation helpers."""
import json
import re
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
            fallback_confidence = float(getattr(self, "self_rag_confidence_threshold", 0.58))
            return {"supported": True, "confidence": fallback_confidence, "feedback": "fallback"}

    @staticmethod
    def _answer_matches_expectation(answer: str, expected_keywords: List[str], expected_answer: str) -> bool:
        normalized_answer = (answer or "").lower()
        if expected_answer:
            expected_terms = [token for token in re.findall(r"[A-Za-z0-9À-ỹ]{4,}", expected_answer.lower())]
            if expected_terms:
                overlap = sum(1 for token in set(expected_terms) if token in normalized_answer)
                if overlap >= max(1, int(len(set(expected_terms)) * 0.5)):
                    return True

        cleaned_keywords = [str(item).strip().lower() for item in expected_keywords if str(item).strip()]
        if cleaned_keywords and all(keyword in normalized_answer for keyword in cleaned_keywords):
            return True

        return False

    def calibrate_self_rag_threshold(
        self,
        evaluation_set: List[Dict[str, Any]],
        top_k: int = 3,
        retrieval_mode: str = "hybrid",
        run_ragas: bool = False,
        persist_artifact: bool = False,
    ) -> Dict[str, Any]:
        if not evaluation_set:
            raise ValueError("evaluation_set không được rỗng")

        calibration_rows: List[Dict[str, Any]] = []
        ragas_rows: List[Dict[str, Any]] = []
        for idx, case in enumerate(evaluation_set):
            question = str(case.get("question", "")).strip()
            if not question:
                raise ValueError(f"evaluation_set[{idx}].question không hợp lệ")

            expected_keywords = case.get("expected_keywords") or []
            if not isinstance(expected_keywords, list):
                raise ValueError(f"evaluation_set[{idx}].expected_keywords phải là list")

            expected_answer = str(case.get("expected_answer", "")).strip()

            result = self.chat(
                question=question,
                history=[],
                top_k=max(1, top_k),
                retrieval_mode=retrieval_mode,
                use_reranker=True,
                use_self_rag=False,
            )
            self_check = result.get("self_check", {}) or {}
            confidence = float(self_check.get("confidence", 0.0))
            supported = bool(self_check.get("supported", True))
            answer = str(result.get("answer", ""))

            is_correct = self._answer_matches_expectation(
                answer=answer,
                expected_keywords=expected_keywords,
                expected_answer=expected_answer,
            )
            calibration_rows.append(
                {
                    "question": question,
                    "confidence": confidence,
                    "supported": supported,
                    "is_correct": is_correct,
                }
            )
            ragas_rows.append(
                {
                    "question": question,
                    "answer": answer,
                    "contexts": [item.get("content", "") for item in result.get("contexts", [])],
                    "expected_answer": expected_answer,
                }
            )

        best_threshold = float(getattr(self, "self_rag_confidence_threshold", 0.58))
        best_f1 = -1.0
        best_stats: Dict[str, Any] = {}

        for step in range(20, 91, 5):
            threshold = step / 100.0
            tp = fp = fn = tn = 0

            for row in calibration_rows:
                label_retry = not row["is_correct"]
                pred_retry = (not row["supported"]) or row["confidence"] < threshold

                if pred_retry and label_retry:
                    tp += 1
                elif pred_retry and not label_retry:
                    fp += 1
                elif not pred_retry and label_retry:
                    fn += 1
                else:
                    tn += 1

            precision = tp / (tp + fp) if (tp + fp) else 0.0
            recall = tp / (tp + fn) if (tp + fn) else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

            if f1 > best_f1:
                best_f1 = f1
                best_threshold = threshold
                best_stats = {
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "f1": round(f1, 4),
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                    "tn": tn,
                }

        self.self_rag_confidence_threshold = round(best_threshold, 4)
        report = {
            "threshold": self.self_rag_confidence_threshold,
            "metrics": best_stats,
            "samples": len(calibration_rows),
            "rows": calibration_rows,
        }

        use_ragas = bool(run_ragas or getattr(self, "enable_ragas_in_calibration", False))
        if use_ragas:
            from .ragas_eval import run_ragas_evaluation

            report["ragas"] = run_ragas_evaluation(ragas_rows)

        should_persist = bool(persist_artifact or getattr(self, "persist_calibration_artifacts", False))
        if should_persist:
            from .ragas_eval import persist_calibration_artifact

            artifact_path = persist_calibration_artifact(
                report,
                artifact_dir=getattr(self, "calibration_artifact_dir"),
            )
            report["artifact_path"] = artifact_path

        return report

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
