import logging
from datetime import datetime, timezone

import db


def _format_seconds(total: float) -> str:
    s = int(total)
    if s >= 3600:
        hours = s // 3600
        mins = (s % 3600) // 60
        return f"{hours} hr {mins} min"
    if s >= 60:
        return f"{s // 60} min"
    return f"{s} sec"


def score_workflow(workflow: dict) -> float:
    freq = workflow.get("frequency") or 0
    avg = workflow.get("avg_duration_seconds") or 0.0
    try:
        return float(freq) * float(avg)
    except Exception:
        return 0.0


def rank_workflows(workflows: list[dict]) -> list[dict]:
    try:
        for w in workflows:
            s = score_workflow(w)
            w["score"] = s
            w["time_wasted_seconds"] = s
            w["time_wasted_human"] = _format_seconds(s)
        return sorted(workflows, key=lambda w: w["score"], reverse=True)
    except Exception:
        logging.exception("rank_workflows error")
        return workflows


def get_ranked_workflows() -> list[dict]:
    try:
        workflows = db.get_workflows()
        return rank_workflows(workflows)
    except Exception:
        logging.exception("get_ranked_workflows error")
        return []


def get_summary_stats() -> dict:
    try:
        ranked = get_ranked_workflows()

        if not ranked:
            return {
                "total_workflows": 0,
                "total_time_wasted_seconds": 0.0,
                "total_time_wasted_human": "0 sec",
                "top_workflow": None,
                "weekly_wasted_seconds": 0.0,
                "weekly_wasted_human": "0 sec",
            }

        total_seconds = sum(w.get("time_wasted_seconds", 0.0) for w in ranked)

        first_seen_values = [
            w["first_seen"] for w in ranked if w.get("first_seen")
        ]
        if first_seen_values:
            earliest_str = min(first_seen_values)
            try:
                earliest = datetime.fromisoformat(earliest_str.replace("Z", "+00:00"))
                if earliest.tzinfo is None:
                    earliest = earliest.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                weeks = max(1.0, (now - earliest).total_seconds() / 604800)
            except Exception:
                weeks = 1.0
        else:
            weeks = 1.0

        weekly = total_seconds / weeks

        return {
            "total_workflows": len(ranked),
            "total_time_wasted_seconds": total_seconds,
            "total_time_wasted_human": _format_seconds(total_seconds),
            "top_workflow": ranked[0],
            "weekly_wasted_seconds": weekly,
            "weekly_wasted_human": _format_seconds(weekly),
        }

    except Exception:
        logging.exception("get_summary_stats error")
        return {
            "total_workflows": 0,
            "total_time_wasted_seconds": 0.0,
            "total_time_wasted_human": "0 sec",
            "top_workflow": None,
            "weekly_wasted_seconds": 0.0,
            "weekly_wasted_human": "0 sec",
        }
