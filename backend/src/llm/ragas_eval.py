"""RAGAS evaluation helpers for self-rag calibration artifacts."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List


def _as_serializable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _as_serializable(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_as_serializable(item) for item in value]
    return str(value)


def run_ragas_evaluation(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {"enabled": False, "error": "no_rows"}

    try:
        from datasets import Dataset
        from ragas import evaluate
    except Exception as exc:
        return {
            "enabled": False,
            "error": f"RAGAS dependencies unavailable: {str(exc)}",
        }

    try:
        from ragas.metrics import answer_relevancy, context_precision, faithfulness

        metrics = [faithfulness, answer_relevancy, context_precision]
    except Exception:
        try:
            from ragas.metrics import AnswerRelevancy, ContextPrecision, Faithfulness

            metrics = [Faithfulness(), AnswerRelevancy(), ContextPrecision()]
        except Exception as exc:
            return {
                "enabled": False,
                "error": f"RAGAS metrics unavailable: {str(exc)}",
            }

    dataset = Dataset.from_dict(
        {
            "question": [str(row.get("question", "")) for row in rows],
            "answer": [str(row.get("answer", "")) for row in rows],
            "contexts": [list(row.get("contexts", [])) for row in rows],
            "ground_truth": [str(row.get("expected_answer", "")) for row in rows],
        }
    )

    try:
        result = evaluate(dataset=dataset, metrics=metrics)
    except Exception as exc:
        return {
            "enabled": False,
            "error": f"RAGAS evaluate failed: {str(exc)}",
        }

    report: Dict[str, Any] = {"enabled": True}

    if hasattr(result, "to_pandas"):
        try:
            frame = result.to_pandas()
            report["rows"] = len(frame)
            report["columns"] = [str(col) for col in frame.columns]
            means = {}
            for col in frame.columns:
                try:
                    means[str(col)] = float(frame[col].mean())
                except Exception:
                    continue
            report["means"] = means
        except Exception:
            report["rows"] = len(rows)

    if hasattr(result, "scores"):
        try:
            report["scores"] = _as_serializable(result.scores)
        except Exception:
            pass

    return report


def persist_calibration_artifact(report: Dict[str, Any], artifact_dir: Path) -> str:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = artifact_dir / f"self_rag_calibration_{timestamp}.json"

    payload = {
        "version": timestamp,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **_as_serializable(report),
    }

    artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    latest_path = artifact_dir / "latest.json"
    latest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return str(artifact_path)
