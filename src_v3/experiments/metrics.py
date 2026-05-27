"""Small metric helpers for v2 smoke experiments."""

from __future__ import annotations


def summarize_guideline_result(result: dict) -> dict:
    verification = result["verification"]
    conflicts = result["conflicts"]
    issue_summary = summarize_issue_severity(result)
    return {
        "passed": result["evidence"]["verified"],
        "violation_count": len(verification.get("violations", [])),
        "hard_violation_count": issue_summary["hard_violation_count"],
        "soft_target_miss_count": issue_summary["soft_target_miss_count"],
        "missing_data_count": len(verification.get("missing_data", [])),
        "conflict_count": len(conflicts.get("conflicts", [])),
        "active_constraint_count": len(result.get("active_constraints", [])),
        "has_hard_safety_issue": issue_summary["has_hard_safety_issue"],
        "has_soft_target_miss": issue_summary["has_soft_target_miss"],
    }


def conflict_detected_for(result: dict, nutrient: str) -> bool:
    if not nutrient:
        return False
    return any(conflict.get("nutrient") == nutrient for conflict in result["conflicts"].get("conflicts", []))


def summarize_issue_severity(result: dict) -> dict:
    violations = result["verification"].get("violations", [])
    conflicts = result["conflicts"].get("conflicts", [])
    active_constraint_types = _constraint_type_lookup(result)

    hard_violations = []
    soft_misses = []
    other_violations = []
    for violation in violations:
        constraint_type = active_constraint_types.get(violation.get("constraint_id"), "")
        enriched = {**violation, "constraint_type": constraint_type}
        if constraint_type == "hard":
            hard_violations.append(enriched)
        elif constraint_type == "soft":
            soft_misses.append(enriched)
        else:
            other_violations.append(enriched)

    return {
        "hard_violation_count": len(hard_violations),
        "soft_target_miss_count": len(soft_misses),
        "other_violation_count": len(other_violations),
        "conflict_count": len(conflicts),
        "has_hard_safety_issue": bool(hard_violations or conflicts),
        "has_soft_target_miss": bool(soft_misses),
        "hard_violations": hard_violations,
        "soft_target_misses": soft_misses,
        "other_violations": other_violations,
    }


def _constraint_type_lookup(result: dict) -> dict[str, str]:
    details = result.get("active_constraint_details", [])
    if details:
        return {
            item.get("constraint_id"): item.get("constraint_type", "")
            for item in details
        }
    return {}
