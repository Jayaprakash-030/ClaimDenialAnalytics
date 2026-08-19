"""Generate prior authorization records for PA-required service events.

Design: service events → PAs → claims. Each PA row is the pre-service decision
for one event_id so later adjudication can look up a real PA instead of
inventing CO-197.

status:
  approved         — payer said yes
  denied           — payer said no before the service
  never_requested  — no PA was filed

match_quality:
  exact      — PA covers this member/provider/dates (claim should pass PA check)
  unmatched  — PA exists but wrong provider or dates (wrongful CO-197 seed)
  none       — no usable matching PA (never requested or denied)
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from generator.members import generate_members
from generator.providers import generate_providers
from generator.reference_data import load_config
from generator.save_tables import save_csv
from generator.service_events import generate_service_events

# Share of PA-required events. Among never_requested + unmatched, 60/40 matches config.
_OUTCOME_LABELS = np.array(["exact", "never_requested", "unmatched", "denied"])
_OUTCOME_P = np.array([0.88, 0.06, 0.04, 0.02])


def _other_provider(
    rng: np.random.Generator,
    current_id: str,
    provider_type: str,
    pools: dict[str, np.ndarray],
) -> str:
    pool = pools.get(provider_type, np.array([]))
    others = pool[pool != current_id]
    if len(others) == 0:
        return current_id
    return str(rng.choice(others))


def generate_prior_auths(
    events: pd.DataFrame,
    providers: pd.DataFrame,
    config: dict | None = None,
) -> pd.DataFrame:
    """One PA row per PA-required service event."""
    cfg = config if config is not None else load_config()
    rng = np.random.default_rng(cfg["seed"])

    pa_events = events.loc[events["pa_required"]].reset_index(drop=True)
    n = len(pa_events)
    outcomes = rng.choice(_OUTCOME_LABELS, size=n, p=_OUTCOME_P)

    type_by_id = providers.set_index("provider_id")["provider_type"].to_dict()
    pools = {
        ptype: grp["provider_id"].to_numpy()
        for ptype, grp in providers.groupby("provider_type", sort=False)
    }

    rows: list[dict] = []
    for i, event in pa_events.iterrows():
        outcome = outcomes[i]
        service_date = event["service_date"].date()
        event_provider = str(event["provider_id"])
        ptype = type_by_id.get(event_provider, "")

        status = "approved"
        match_quality = "exact"
        pa_provider = event_provider
        decision_date = None
        auth_start = None
        auth_end = None

        if outcome == "never_requested":
            status = "never_requested"
            match_quality = "none"
        elif outcome == "denied":
            status = "denied"
            match_quality = "none"
            lead = int(rng.integers(3, 22))
            decision_date = service_date - timedelta(days=lead)
        elif outcome == "unmatched":
            status = "approved"
            match_quality = "unmatched"
            lead = int(rng.integers(3, 22))
            decision_date = service_date - timedelta(days=lead)
            # Wrong provider and/or expired window so M6 cannot match this event
            mismatch_mode = rng.choice(["provider", "dates", "both"], p=[0.40, 0.40, 0.20])
            if mismatch_mode in {"provider", "both"}:
                pa_provider = _other_provider(rng, event_provider, ptype, pools)
            if mismatch_mode in {"dates", "both"} or pa_provider == event_provider:
                # Window ends before the service date
                gap = int(rng.integers(1, 21))
                auth_end = service_date - timedelta(days=gap)
                span = int(rng.integers(14, 45))
                auth_start = auth_end - timedelta(days=span)
                decision_date = auth_start
            else:
                auth_start = decision_date
                auth_end = service_date + timedelta(days=int(rng.integers(14, 61)))
        else:
            # exact match
            lead = int(rng.integers(3, 22))
            decision_date = service_date - timedelta(days=lead)
            auth_start = decision_date
            auth_end = service_date + timedelta(days=int(rng.integers(14, 61)))

        rows.append(
            {
                "pa_id": f"PA{i + 1:06d}",
                "event_id": event["event_id"],
                "member_id": event["member_id"],
                "provider_id": pa_provider,
                "service_line_id": event["service_line_id"],
                "cpt_code": event["cpt_code"],
                "status": status,
                "match_quality": match_quality,
                "decision_date": decision_date,
                "auth_start": auth_start,
                "auth_end": auth_end,
            }
        )

    df = pd.DataFrame(rows)
    for col in ("decision_date", "auth_start", "auth_end"):
        df[col] = pd.to_datetime(df[col])
    return df


if __name__ == "__main__":
    cfg = load_config()
    members = generate_members(cfg)
    providers = generate_providers(cfg)
    events = generate_service_events(members, providers, cfg)
    prior_auths = generate_prior_auths(events, providers, cfg)

    pa_n = int(events["pa_required"].sum())
    print(prior_auths.head())
    print()
    print(f"PA rows: {len(prior_auths):,} (PA-required events: {pa_n:,})")
    print()
    print("status mix:")
    print(prior_auths["status"].value_counts(normalize=True).round(3))
    print()
    print("match_quality mix:")
    print(prior_auths["match_quality"].value_counts(normalize=True).round(3))

    bad = prior_auths.loc[prior_auths["match_quality"].isin(["none", "unmatched"])]
    never = (bad["status"] == "never_requested").sum()
    unmatched = (bad["match_quality"] == "unmatched").sum()
    denied = (bad["status"] == "denied").sum()
    fail_modes = never + unmatched
    print()
    print(f"never_requested / unmatched among CO-197 seeds: {never} / {unmatched} "
          f"({never / fail_modes:.2%} / {unmatched / fail_modes:.2%})"
          if fail_modes else "no failure modes")
    print(f"PA denied up front: {denied}")

    merged = prior_auths.merge(
        events[["event_id", "provider_id", "service_date", "pa_required"]],
        on="event_id",
        suffixes=("_pa", "_event"),
    )
    exact = merged["match_quality"] == "exact"
    covers = (
        exact
        & (merged["provider_id_pa"] == merged["provider_id_event"])
        & (merged["auth_start"] <= merged["service_date"])
        & (merged["auth_end"] >= merged["service_date"])
    )
    print(f"Exact rows that actually cover the event: {covers.sum():,} / {exact.sum():,}")
    print(
        "Non-PA service lines in PA table:",
        merged.loc[~merged["pa_required"], "service_line_id"].unique().tolist(),
    )

    save_csv(prior_auths, "prior_auths")
