"""Interval-intersection conflict detection for comorbidity constraints."""

from __future__ import annotations

from collections import defaultdict

from .models import NutrientConstraint


PRIORITY_RANK = {
    "safety-critical": 4,
    "disease-therapeutic": 3,
    "general-DRI": 2,
    "preference": 1,
}


def detect_interval_conflicts(constraints: list[NutrientConstraint]) -> dict:
    grouped: dict[str, list[NutrientConstraint]] = defaultdict(list)
    for constraint in constraints:
        grouped[constraint.nutrient].append(constraint)

    conflicts: list[dict] = []
    merged: dict[str, dict] = {}

    for nutrient, items in grouped.items():
        lowers = [c.lower_bound for c in items if c.lower_bound is not None]
        uppers = [c.upper_bound for c in items if c.upper_bound is not None]
        merged_lower = max(lowers) if lowers else None
        merged_upper = min(uppers) if uppers else None

        merged[nutrient] = {
            "lower_bound": merged_lower,
            "upper_bound": merged_upper,
            "constraints": [c.constraint_id for c in items],
        }

        if merged_lower is not None and merged_upper is not None and merged_lower > merged_upper:
            sorted_items = sorted(
                items,
                key=lambda c: PRIORITY_RANK.get(c.priority, 0),
                reverse=True,
            )
            conflicts.append({
                "nutrient": nutrient,
                "merged_lower": merged_lower,
                "merged_upper": merged_upper,
                "conflict_type": _classify_conflict(items),
                "constraints": [
                    {
                        "constraint_id": c.constraint_id,
                        "disease": c.disease,
                        "lower_bound": c.lower_bound,
                        "upper_bound": c.upper_bound,
                        "unit": c.unit,
                        "priority": c.priority,
                        "source": c.source,
                        "condition": c.condition,
                    }
                    for c in items
                ],
                "resolution": {
                    "selected_constraint_id": sorted_items[0].constraint_id,
                    "reason": f"highest priority: {sorted_items[0].priority}",
                },
            })

    return {
        "has_conflict": len(conflicts) > 0,
        "conflicts": conflicts,
        "merged_intervals": merged,
    }


def _classify_conflict(items: list[NutrientConstraint]) -> str:
    hard_count = sum(1 for c in items if c.constraint_type == "hard")
    if hard_count >= 2:
        return "hard_conflict"
    if hard_count == 1:
        return "soft_hard_conflict"
    return "soft_conflict"

