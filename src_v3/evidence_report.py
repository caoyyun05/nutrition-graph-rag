"""Evidence traceability report helpers."""

from __future__ import annotations


def build_evidence_report(
    verification_result: dict,
    conflict_result: dict,
) -> dict:
    return {
        "verified": verification_result.get("passed", False) and not conflict_result.get("has_conflict", False),
        "violations": verification_result.get("violations", []),
        "missing_data": verification_result.get("missing_data", []),
        "conflicts": conflict_result.get("conflicts", []),
        "evidence_sources": _collect_sources(verification_result, conflict_result),
    }


def _collect_sources(verification_result: dict, conflict_result: dict) -> list[str]:
    sources: set[str] = set()
    for violation in verification_result.get("violations", []):
        if violation.get("source"):
            sources.add(violation["source"])
    for conflict in conflict_result.get("conflicts", []):
        for constraint in conflict.get("constraints", []):
            if constraint.get("source"):
                sources.add(constraint["source"])
    return sorted(sources)

