"""Generate planned service events — the source of truth for PAs (M4) and claims (M5).

Design: service events first, then prior auths, then claims. Each event_id links
the planned episode of care across those tables so PA matching stays consistent.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from generator.members import generate_members
from generator.providers import generate_providers
from generator.save_tables import save_csv
from generator.reference_data import (
    get_cpt_codes,
    get_icd10_codes,
    get_service_lines,
    load_config,
)

# Preferred provider_type(s) per service line for realistic pairing
_SERVICE_LINE_PROVIDER_TYPES: dict[str, list[str]] = {
    "office_visit": ["independent_physician", "ambulatory_clinic"],
    "ed": ["hospital"],
    "lab": ["lab"],
    "imaging": ["imaging_center"],
    "outpatient_surgery": ["hospital"],
    "inpatient_surgery": ["hospital"],
    "pt": ["pt_clinic"],
}


def _provider_pools(providers: pd.DataFrame) -> dict[str, np.ndarray]:
    """Map each service_line_id to an array of eligible provider_ids."""
    pools: dict[str, np.ndarray] = {}
    all_ids = providers["provider_id"].to_numpy()
    for service_line_id, types in _SERVICE_LINE_PROVIDER_TYPES.items():
        matched = providers.loc[
            providers["provider_type"].isin(types), "provider_id"
        ].to_numpy()
        # Prefer in-network when available; fall back to matched types, then anyone
        in_net = providers.loc[
            providers["provider_type"].isin(types) & providers["in_network"],
            "provider_id",
        ].to_numpy()
        if len(in_net) > 0:
            pools[service_line_id] = in_net
        elif len(matched) > 0:
            pools[service_line_id] = matched
        else:
            pools[service_line_id] = all_ids
    return pools


def _cpt_pools(cpts: pd.DataFrame) -> dict[str, np.ndarray]:
    return {
        sid: grp["cpt_code"].to_numpy()
        for sid, grp in cpts.groupby("service_line_id", sort=False)
    }


def generate_service_events(
    members: pd.DataFrame,
    providers: pd.DataFrame,
    config: dict | None = None,
) -> pd.DataFrame:
    """Build planned care episodes over the simulation window."""
    cfg = config if config is not None else load_config()
    seed = cfg["seed"]
    n = cfg["counts"]["claims"]
    window_start = date.fromisoformat(cfg["simulation"]["start_date"])
    window_end = date.fromisoformat(cfg["simulation"]["end_date"])
    window_days = (window_end - window_start).days

    rng = np.random.default_rng(seed)

    lines = get_service_lines()
    cpts = get_cpt_codes()
    icds = get_icd10_codes()

    line_ids = lines["service_line_id"].to_numpy()
    line_shares = lines["volume_share"].to_numpy(dtype=float)
    line_shares = line_shares / line_shares.sum()
    pa_flags = dict(zip(lines["service_line_id"], lines["pa_required"]))

    service_line_ids = rng.choice(line_ids, size=n, p=line_shares)
    member_ids = rng.choice(members["member_id"].to_numpy(), size=n)

    pools = _provider_pools(providers)
    cpt_by_line = _cpt_pools(cpts)
    icd_codes = icds["icd10_code"].to_numpy()

    provider_ids = np.empty(n, dtype=object)
    cpt_codes = np.empty(n, dtype=object)
    for sid in line_ids:
        mask = service_line_ids == sid
        k = int(mask.sum())
        if k == 0:
            continue
        provider_ids[mask] = rng.choice(pools[sid], size=k)
        cpt_codes[mask] = rng.choice(cpt_by_line[sid], size=k)

    # Base uniform dates, plus a mild tilt toward the second half of the window
    day_offsets = rng.integers(0, window_days + 1, size=n)
    growth_boost = rng.random(n) < 0.15
    day_offsets = np.where(
        growth_boost,
        rng.integers(window_days // 2, window_days + 1, size=n),
        day_offsets,
    )

    service_dates = [window_start + timedelta(days=int(d)) for d in day_offsets]
    icd10_codes = rng.choice(icd_codes, size=n)
    pa_required = np.array([pa_flags[sid] for sid in service_line_ids])

    df = pd.DataFrame(
        {
            "event_id": [f"E{i + 1:06d}" for i in range(n)],
            "member_id": member_ids,
            "provider_id": provider_ids,
            "service_line_id": service_line_ids,
            "service_date": service_dates,
            "cpt_code": cpt_codes,
            "icd10_code": icd10_codes,
            "pa_required": pa_required,
        }
    )
    df["service_date"] = pd.to_datetime(df["service_date"])
    return df


if __name__ == "__main__":
    cfg = load_config()
    members = generate_members(cfg)
    providers = generate_providers(cfg)
    events = generate_service_events(members, providers, cfg)

    print(events.head())
    print()
    print(f"Count: {len(events)} (target {cfg['counts']['claims']})")
    print()
    print("Service line mix:")
    print(events["service_line_id"].value_counts(normalize=True).round(3))
    print()
    print(f"PA-required share: {events['pa_required'].mean():.3f}")
    print(
        "PA-required lines only:",
        sorted(events.loc[events["pa_required"], "service_line_id"].unique()),
    )
    print()
    # CPT belongs to service line
    cpts = get_cpt_codes()
    merged = events.merge(
        cpts[["cpt_code", "service_line_id"]], on="cpt_code", suffixes=("", "_cpt")
    )
    mismatches = (merged["service_line_id"] != merged["service_line_id_cpt"]).sum()
    print(f"CPT/service-line mismatches: {mismatches}")
    print(
        f"Date range: {events['service_date'].min().date()} → {events['service_date'].max().date()}"
    )
    save_csv(members, "members")
    save_csv(providers, "providers")
    save_csv(events, "service_events")
