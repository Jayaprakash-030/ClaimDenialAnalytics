"""Recompute Phase 1 KPIs from data/raw/ and compare to config targets."""

from __future__ import annotations

import sys
from dataclasses import dataclass

import pandas as pd

from generator.reference_data import load_config
from generator.save_tables import RAW_DIR

RATE_TOLERANCE = 0.02


@dataclass
class CheckResult:
    name: str
    target: str
    actual: str
    ok: bool
    structural: bool = False


def _load(name: str) -> pd.DataFrame:
    path = RAW_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run: uv run python -m generator.run"
        )
    return pd.read_csv(path)


def _parse_dates(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col])
    return out


def validate(config: dict | None = None) -> list[CheckResult]:
    cfg = config if config is not None else load_config()
    targets = cfg["targets"]
    results: list[CheckResult] = []

    adjudicated = _parse_dates(
        _load("adjudicated_claims"),
        ["service_date", "received_date", "decision_date"],
    )
    appeals = _parse_dates(
        _load("appeals"),
        ["filed_date", "appeal_decision_date"],
    )
    members = _load("members")
    prior_auths = _load("prior_auths")

    n = len(adjudicated)
    rejected = adjudicated["status"] == "rejected"
    denied = adjudicated["status"] == "denied"
    paid = adjudicated["status"] == "paid"
    adjudicated_denominator = paid | denied

    def add_rate(name: str, target: float, actual: float) -> None:
        ok = abs(actual - target) <= RATE_TOLERANCE
        results.append(
            CheckResult(
                name=name,
                target=f"{target:.1%}",
                actual=f"{actual:.1%}",
                ok=ok,
            )
        )

    lob_shares = members["lob_id"].value_counts(normalize=True)
    blended_denial_target = sum(
        targets["denial_rate_by_lob"][lob] * lob_shares[lob] for lob in lob_shares.index
    )
    add_rate(
        "denial_rate (paid+denied denominator)",
        blended_denial_target,
        denied.sum() / adjudicated_denominator.sum() if adjudicated_denominator.any() else 0.0,
    )
    add_rate(
        "front_end_rejection",
        cfg["rates"]["front_end_rejection"],
        rejected.sum() / n,
    )

    adj_members = adjudicated.merge(
        members[["member_id", "lob_id"]], on="member_id", how="left"
    )
    for lob_id, target in targets["denial_rate_by_lob"].items():
        mask = adj_members["lob_id"] == lob_id
        denom = adj_members.loc[mask, "status"].isin(["paid", "denied"]).sum()
        if denom == 0:
            continue
        actual = (adj_members.loc[mask, "status"] == "denied").sum() / denom
        add_rate(f"denial_rate_{lob_id}", float(target), float(actual))

    denied_n = int(denied.sum())
    appeal_rate = len(appeals) / denied_n if denied_n else 0.0
    add_rate("appeal_rate_of_denials", targets["appeal_rate_of_denials"], appeal_rate)

    if not appeals.empty:
        for category, target in targets["overturn_rate_by_category"].items():
            subset = appeals[appeals["cause_category"] == category]
            if len(subset) < 25:
                results.append(
                    CheckResult(
                        name=f"overturn_rate_{category}",
                        target=f"{target:.1%}",
                        actual="n/a (too few appeals)",
                        ok=True,
                    )
                )
                continue
            actual = (subset["outcome"] == "overturned").mean()
            add_rate(f"overturn_rate_{category}", float(target), float(actual))

    paid_rows = adjudicated[paid]
    if not paid_rows.empty:
        recon = (
            paid_rows["paid_amount"]
            + paid_rows["contractual_adjustment"]
            + paid_rows["patient_responsibility"]
            - paid_rows["billed_amount"]
        ).abs()
        max_recon = float(recon.max())
        results.append(
            CheckResult(
                name="paid_claim_reconciliation",
                target="max diff = $0.00",
                actual=f"max diff = ${max_recon:.4f}",
                ok=max_recon < 0.01,
                structural=True,
            )
        )

    co197_non_pa = adjudicated[
        (~adjudicated["pa_required"]) & (adjudicated["denial_carc"] == "CO-197")
    ]
    results.append(
        CheckResult(
            name="no_CO-197_on_non_PA_claims",
            target="0",
            actual=str(len(co197_non_pa)),
            ok=len(co197_non_pa) == 0,
            structural=True,
        )
    )

    rej_bad = adjudicated[
        rejected
        & (
            adjudicated["denial_carc"].notna()
            | adjudicated["paid_amount"].notna()
        )
    ]
    results.append(
        CheckResult(
            name="rejected_claims_have_no_decision_fields",
            target="0 violations",
            actual=f"{len(rej_bad)} violations",
            ok=len(rej_bad) == 0,
            structural=True,
        )
    )

    appeal_claim_ids = set(appeals["claim_id"])
    denied_ids = set(adjudicated.loc[denied, "claim_id"])
    bad_appeals = appeal_claim_ids - denied_ids
    results.append(
        CheckResult(
            name="appeals_only_on_denied_claims",
            target="0 violations",
            actual=f"{len(bad_appeals)} violations",
            ok=len(bad_appeals) == 0,
            structural=True,
        )
    )

    non_rejected = adjudicated[~rejected]
    date_ok = (
        (non_rejected["received_date"] >= non_rejected["service_date"])
        & (non_rejected["decision_date"] >= non_rejected["received_date"])
    ).all()
    results.append(
        CheckResult(
            name="service <= received <= decision",
            target="all rows",
            actual="ok" if date_ok else "violations found",
            ok=bool(date_ok),
            structural=True,
        )
    )

    if not appeals.empty:
        appeal_dates = appeals.merge(
            adjudicated[["claim_id", "decision_date"]], on="claim_id", how="left"
        )
        appeals_ok = (
            (appeal_dates["filed_date"] > appeal_dates["decision_date"])
            & (appeal_dates["appeal_decision_date"] > appeal_dates["filed_date"])
        ).all()
        results.append(
            CheckResult(
                name="decision < appeal_filed < appeal_decided",
                target="all appeals",
                actual="ok" if appeals_ok else "violations found",
                ok=bool(appeals_ok),
                structural=True,
            )
        )

    if not appeals.empty and "event_id" in appeals.columns:
        co197 = appeals[appeals["denial_carc"] == "CO-197"].merge(
            prior_auths[["event_id", "match_quality", "status"]],
            on="event_id",
            how="left",
        )
        unmatched = co197[co197["match_quality"] == "unmatched"]
        fair = co197[co197["status"] == "never_requested"]
        if len(unmatched) >= 10 and len(fair) >= 10:
            u_rate = (unmatched["outcome"] == "overturned").mean()
            f_rate = (fair["outcome"] == "overturned").mean()
            results.append(
                CheckResult(
                    name="CO-197_unmatched_overturn > never_requested",
                    target="unmatched higher",
                    actual=f"unmatched={u_rate:.1%}, never_requested={f_rate:.1%}",
                    ok=u_rate > f_rate,
                    structural=True,
                )
            )

    return results


def print_report(results: list[CheckResult]) -> bool:
    width = max(len(r.name) for r in results) if results else 20
    print(f"{'Check':<{width}}  {'Target':<22}  {'Actual':<22}  OK")
    print("-" * (width + 54))
    for r in results:
        mark = "yes" if r.ok else "NO"
        print(f"{r.name:<{width}}  {r.target:<22}  {r.actual:<22}  {mark}")

    structural = [r for r in results if r.structural]
    calibration = [r for r in results if not r.structural]
    structural_pass = all(r.ok for r in structural)
    calibration_pass = all(r.ok for r in calibration)

    print()
    print(f"Structural checks: {'PASS' if structural_pass else 'FAIL'}")
    print(f"Calibration checks (±{RATE_TOLERANCE:.0%}): {'PASS' if calibration_pass else 'FAIL'}")
    print()
    print("PASS" if structural_pass else "FAIL")
    return structural_pass


def main() -> None:
    try:
        results = validate()
    except FileNotFoundError as exc:
        print(exc)
        sys.exit(1)
    passed = print_report(results)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
