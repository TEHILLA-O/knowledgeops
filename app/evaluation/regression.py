"""Evaluation regression and quality gates."""

from dataclasses import dataclass

from app.core.config import Settings
from app.core.exceptions import QualityGateError


@dataclass
class RegressionReport:
    baseline_metrics: dict[str, float]
    candidate_metrics: dict[str, float]
    deltas: dict[str, float]
    passed: bool
    failures: list[str]


def compare_metrics(
    baseline: dict[str, float],
    candidate: dict[str, float],
    *,
    tolerance: float = 0.05,
    required_keys: list[str] | None = None,
) -> RegressionReport:
    """Compare candidate metrics against baseline with tolerance."""
    required_keys = required_keys or ["hit_rate_at_5", "mrr", "ndcg_at_5"]
    deltas: dict[str, float] = {}
    failures: list[str] = []

    for key in required_keys:
        base_val = float(baseline.get(key, 0.0))
        cand_val = float(candidate.get(key, 0.0))
        delta = cand_val - base_val
        deltas[key] = delta
        if delta < -tolerance:
            failures.append(f"{key} regressed by {abs(delta):.4f} (baseline={base_val:.4f}, candidate={cand_val:.4f})")

    return RegressionReport(
        baseline_metrics=baseline,
        candidate_metrics=candidate,
        deltas=deltas,
        passed=len(failures) == 0,
        failures=failures,
    )


def apply_quality_gates(
    metrics: dict[str, float],
    settings: Settings | None = None,
) -> tuple[bool, list[str]]:
    """Check metrics against configured quality gates."""
    from app.core.config import get_settings

    settings = settings or get_settings()
    gates = settings.retrieval_config.get("quality_gates", {})
    failures: list[str] = []

    hit_min = float(gates.get("hit_rate_at_5_min", 0.6))
    mrr_min = float(gates.get("mrr_min", 0.5))

    hit_rate = float(metrics.get("hit_rate_at_5", 0.0))
    mrr = float(metrics.get("mrr", 0.0))

    if hit_rate < hit_min:
        failures.append(f"hit_rate_at_5 {hit_rate:.4f} below minimum {hit_min:.4f}")
    if mrr < mrr_min:
        failures.append(f"mrr {mrr:.4f} below minimum {mrr_min:.4f}")

    return len(failures) == 0, failures


def enforce_quality_gates(
    metrics: dict[str, float],
    settings: Settings | None = None,
) -> None:
    """Raise QualityGateError if metrics fail gates."""
    passed, failures = apply_quality_gates(metrics, settings)
    if not passed:
        raise QualityGateError("; ".join(failures))


def regression_with_gates(
    baseline: dict[str, float],
    candidate: dict[str, float],
    settings: Settings | None = None,
) -> RegressionReport:
    """Compare regression and validate candidate against quality gates."""
    from app.core.config import get_settings

    settings = settings or get_settings()
    tolerance = float(
        settings.retrieval_config.get("quality_gates", {}).get("regression_tolerance", 0.05)
    )
    report = compare_metrics(baseline, candidate, tolerance=tolerance)
    gate_passed, gate_failures = apply_quality_gates(candidate, settings)
    if not gate_passed:
        report.failures.extend(gate_failures)
        report.passed = False
    return report
