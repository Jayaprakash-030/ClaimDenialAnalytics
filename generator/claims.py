"""Turn service events into submitted claims (the 837).

Each event becomes a billed claim with allowed/billed amounts and a received
date. ~1% extra rows are duplicate submissions (CO-18 feedstock in M6).

This table is bills, not decisions — no pay/deny/CARC here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from generator.members import generate_members
from generator.providers import generate_providers
from generator.reference_data import get_cpt_codes, load_config
from generator.save_tables import save_csv
from generator.service_events import generate_service_events

_RECEIVE_LAG_MIN = 3
_RECEIVE_LAG_MAX = 21


def generate_claims(
    events: pd.DataFrame,
    config: dict | None = None,
) -> pd.DataFrame:
    """Build one claim per event, then append ~1% duplicate submissions."""
    cfg = config if config is not None else load_config()
    rng = np.random.default_rng(cfg["seed"])
    n = len(events)
    dup_share = cfg["rates"]["duplicate_claim_share"]
    mult_min = cfg["rates"]["chargemaster_multiplier_min"]
    mult_max = cfg["rates"]["chargemaster_multiplier_max"]

    cpts = get_cpt_codes()[["cpt_code", "base_allowed"]]
    base = events.merge(cpts, on="cpt_code", how="left")
    if base["base_allowed"].isna().any():
        missing = base.loc[base["base_allowed"].isna(), "cpt_code"].unique()
        raise ValueError(f"CPT codes missing base_allowed: {missing[:10]}")

    noise = rng.uniform(0.90, 1.10, size=n)
    allowed = (base["base_allowed"].to_numpy() * noise).round(2)
    multiplier = rng.uniform(mult_min, mult_max, size=n)
    billed = (allowed * multiplier).round(2)
    lag = rng.integers(_RECEIVE_LAG_MIN, _RECEIVE_LAG_MAX + 1, size=n)
    received = pd.to_datetime(base["service_date"]) + pd.to_timedelta(lag, unit="D")

    originals = pd.DataFrame(
        {
            "claim_id": [f"C{i + 1:06d}" for i in range(n)],
            "event_id": base["event_id"].to_numpy(),
            "member_id": base["member_id"].to_numpy(),
            "provider_id": base["provider_id"].to_numpy(),
            "service_line_id": base["service_line_id"].to_numpy(),
            "cpt_code": base["cpt_code"].to_numpy(),
            "icd10_code": base["icd10_code"].to_numpy(),
            "service_date": pd.to_datetime(base["service_date"]),
            "received_date": received,
            "allowed_amount": allowed,
            "billed_amount": billed,
            "pa_required": base["pa_required"].to_numpy(),
            "is_duplicate": False,
        }
    )

    n_dups = int(round(n * dup_share))
    dup_idx = rng.choice(n, size=n_dups, replace=False)
    duplicates = originals.iloc[dup_idx].copy()
    duplicates["claim_id"] = [f"C{n + i + 1:06d}" for i in range(n_dups)]
    duplicates["is_duplicate"] = True
    # Second submission arrives a bit later than the first
    extra_lag = rng.integers(1, 8, size=n_dups)
    duplicates["received_date"] = duplicates["received_date"] + pd.to_timedelta(
        extra_lag, unit="D"
    )

    claims = pd.concat([originals, duplicates], ignore_index=True)
    return claims


if __name__ == "__main__":
    cfg = load_config()
    members = generate_members(cfg)
    providers = generate_providers(cfg)
    events = generate_service_events(members, providers, cfg)
    claims = generate_claims(events, cfg)

    print(claims.head())
    print()
    print(f"Claims: {len(claims):,} (events {len(events):,} + dups {claims['is_duplicate'].sum():,})")
    print(f"Duplicate share: {claims['is_duplicate'].mean():.3f} (target {cfg['rates']['duplicate_claim_share']})")
    print(f"billed > allowed: {(claims['billed_amount'] > claims['allowed_amount']).all()}")
    print(f"received >= service: {(claims['received_date'] >= claims['service_date']).all()}")
    print(
        f"Every event has a claim: {set(events['event_id']) <= set(claims['event_id'])}"
    )
    print()
    print("Monthly claim volume (received_date):")
    print(
        claims.assign(month=claims["received_date"].dt.to_period("M"))
        .groupby("month")
        .size()
        .head(6)
    )

    save_csv(claims, "claims")
