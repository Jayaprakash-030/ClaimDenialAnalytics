"""Generate appeal records for denied adjudicated claims.

Only status == "denied" claims are appeal-eligible (not rejected or paid).
~12% of denials are filed; overturn probability comes from denial cause_category,
with higher overturn on wrongful CO-197 (prior_auth match_quality == unmatched).
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from generator.adjudication import adujudicate_claims
from generator.claims import generate_claims
from generator.members import generate_members
from generator.prior_auth import generate_prior_auths
from generator.providers import generate_providers
from generator.reference_data import get_carc_codes, load_config
from generator.save_tables import save_csv
from generator.service_events import generate_service_events


def _overturn_probability(
    denial_carc: str,
    cause_category: str,
    pa_row: pd.Series | None,
    overturn_by_category: dict[str, float],
) -> float:
    """CO-197 splits fair vs wrongful using prior_auth state."""
    if denial_carc == "CO-197" and pa_row is not None:
        if pa_row["match_quality"] == "unmatched":
            return float(overturn_by_category["authorization"])
        if pa_row["status"] == "never_requested":
            return float(overturn_by_category["process"])
        if pa_row["status"] == "denied":
            return float(overturn_by_category["process"])
    return float(overturn_by_category.get(cause_category, 0.20))


def generate_appeals(
    adjudicated: pd.DataFrame,
    prior_auths: pd.DataFrame,
    config: dict | None = None,
) -> pd.DataFrame:
    """Build one row per filed appeal (~appeal_rate_of_denials of denied claims)."""
    cfg = config if config is not None else load_config()
    rng = np.random.default_rng(cfg["seed"])
    rates = cfg["rates"]
    targets = cfg["targets"]

    appeal_rate = float(targets["appeal_rate_of_denials"])
    overturn_by_category = targets["overturn_rate_by_category"]
    filing_min = int(rates["appeal_filing_lag_days_min"])
    filing_max = int(rates["appeal_filing_lag_days_max"])
    decision_min = int(rates["appeal_decision_lag_days_min"])
    decision_max = int(rates["appeal_decision_lag_days_max"])

    carc_lookup = get_carc_codes().set_index("carc_code")
    pa_by_event = {
        str(row["event_id"]): row for _, row in prior_auths.iterrows()
    }

    denied = adjudicated.loc[adjudicated["status"] == "denied"].copy()
    if denied.empty:
        return pd.DataFrame(
            columns=[
                "appeal_id",
                "claim_id",
                "event_id",
                "denial_carc",
                "cause_category",
                "filed_date",
                "appeal_decision_date",
                "outcome",
            ]
        )

    rows: list[dict] = []
    appeal_idx = 0
    for claim in denied.itertuples(index=False):
        if rng.random() >= appeal_rate:
            continue

        denial_carc = str(claim.denial_carc)
        if denial_carc not in carc_lookup.index:
            cause_category = "process"
        else:
            cause_category = str(carc_lookup.loc[denial_carc, "cause_category"])

        pa_row = pa_by_event.get(str(claim.event_id))
        overturn_prob = _overturn_probability(
            denial_carc, cause_category, pa_row, overturn_by_category
        )
        outcome = "overturned" if rng.random() < overturn_prob else "upheld"

        claim_decision = pd.to_datetime(claim.decision_date)
        filing_lag = int(rng.integers(filing_min, filing_max + 1))
        decision_lag = int(rng.integers(decision_min, decision_max + 1))
        filed_date = claim_decision + timedelta(days=filing_lag)
        appeal_decision_date = filed_date + timedelta(days=decision_lag)

        appeal_idx += 1
        rows.append(
            {
                "appeal_id": f"AP{appeal_idx:06d}",
                "claim_id": claim.claim_id,
                "event_id": claim.event_id,
                "denial_carc": denial_carc,
                "cause_category": cause_category,
                "filed_date": filed_date,
                "appeal_decision_date": appeal_decision_date,
                "outcome": outcome,
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        for col in ("filed_date", "appeal_decision_date"):
            df[col] = pd.to_datetime(df[col])
    return df


if __name__ == "__main__":
    cfg = load_config()
    members = generate_members(cfg)
    providers = generate_providers(cfg)
    events = generate_service_events(members, providers, cfg)
    prior_auths = generate_prior_auths(events, providers, cfg)
    claims = generate_claims(events, cfg)
    adjudicated = adujudicate_claims(claims, members, providers, prior_auths, cfg)
    appeals = generate_appeals(adjudicated, prior_auths, cfg)

    denied_n = int((adjudicated["status"] == "denied").sum())
    print(appeals.head())
    print()
    print(f"Denied claims: {denied_n:,}")
    print(f"Appeals filed: {len(appeals):,} ({len(appeals) / denied_n:.1%} of denials)")
    print()
    print("Outcome mix:")
    print(appeals["outcome"].value_counts(normalize=True).round(3))
    print()
    co197 = appeals[appeals["denial_carc"] == "CO-197"]
    if not co197.empty:
        merged = co197.merge(
            prior_auths[["event_id", "status", "match_quality"]],
            on="event_id",
            how="left",
        )
        print("CO-197 overturn rate by PA failure mode:")
        for key, grp in merged.groupby(["match_quality", "status"], dropna=False):
            rate = (grp["outcome"] == "overturned").mean()
            print(f"  {key}: {rate:.1%} (n={len(grp)})")

    save_csv(appeals, "appeals")
