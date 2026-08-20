"""Adjudicate submitted claims through the payer pipeline (first-fail-wins)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from generator.claims import generate_claims
from generator.members import generate_members
from generator.prior_auth import generate_prior_auths
from generator.providers import generate_providers
from generator.reference_data import load_config
from generator.service_events import generate_service_events

_CODING_CARCS = np.array(["CO-16", "CO-4", "CO-11", "CO-97", "CO-151"])
_CODING_CARC_WEIGHTS = np.array([0.40, 0.20, 0.20, 0.12, 0.08])


def get_enrollment(members: pd.DataFrame, member_id: str):
    """Look up enrollment span for one member. Returns (start, end) or (None, None)."""
    row = members.loc[
        members["member_id"] == member_id, ["enrollment_start", "enrollment_end"]
    ]
    if row.empty:
        return None, None
    return row.iloc[0]["enrollment_start"], row.iloc[0]["enrollment_end"]


def check_enrollment(
    members: pd.DataFrame,
    member_id: str,
    service_date,
) -> tuple[bool, str | None]:
    """
    Enrollment check (pipeline step 3).

    Returns:
        (True, None) if covered on service_date
        (False, CARC) if denied — CO-109 / CO-26 / CO-27
    """
    enrollment_start, enrollment_end = get_enrollment(members, member_id)

    if enrollment_start is None:
        return False, "CO-109"

    service_date = pd.to_datetime(service_date)
    enrollment_start = pd.to_datetime(enrollment_start)
    enrollment_end = pd.to_datetime(enrollment_end)

    if service_date < enrollment_start:
        return False, "CO-26"
    if pd.notna(enrollment_end) and service_date > enrollment_end:
        return False, "CO-27"

    return True, None


def check_in_network(
    providers: pd.DataFrame, provider_id: str
) -> tuple[bool, str | None]:
    """
    Provider / network check (pipeline step 4).

    Returns:
        (True, None) if provider is in network
        (False, CARC) if denied — CO-B7 (v1: OON / missing provider)
    """
    row = providers.loc[providers["provider_id"] == provider_id, ["in_network"]]
    if row.empty:
        return False, "CO-B7"
    if not bool(row.iloc[0]["in_network"]):
        return False, "CO-B7"
    return True, None


def check_duplicate(is_duplicate: bool) -> tuple[bool, str | None]:
    """
    Duplicate claim check (pipeline step 5).

    Returns:
        (True, None) if this is the original submission
        (False, "CO-18") if this is a duplicate of an earlier claim
    """
    if bool(is_duplicate):
        return False, "CO-18"
    return True, None


def check_code_edits(
    providers: pd.DataFrame,
    provider_id: str,
    rng: np.random.Generator,
) -> tuple[bool, str | None]:
    """
    Code edit check (pipeline step 6).

    v1: probabilistic denial driven by provider billing_quality (not full NCCI).

    Returns:
        (True, None) if coding passes
        (False, CARC) if denied — CO-16 / CO-4 / CO-11 / CO-97 / CO-151
    """
    row = providers.loc[providers["provider_id"] == provider_id, ["billing_quality"]]
    if row.empty:
        return False, "CO-16"

    quality = float(row.iloc[0]["billing_quality"])
    # ~1% for high-quality billers, up to ~10% for problem providers
    denial_prob = 0.01 + 0.10 * (1.0 - quality)
    if rng.random() >= denial_prob:
        return True, None

    carc = rng.choice(_CODING_CARCS, p=_CODING_CARC_WEIGHTS)
    return False, str(carc)


def check_prior_auth(
    pa_row: pd.Series | None,
    provider_id: str,
    service_date,
    pa_required: bool,
) -> tuple[bool, str | None]:
    """
    Prior authorization check (pipeline step 9).

    Looks up the pre-built PA row for this event_id. Denials emerge from
    prior_auths — not random dice.

    Returns:
        (True, None) if PA not required, or a matching approved auth exists
        (False, "CO-197") if required and missing / invalid
    """
    if not bool(pa_required):
        return True, None

    if pa_row is None:
        return False, "CO-197"

    if pa_row["status"] != "approved" or pa_row["match_quality"] != "exact":
        return False, "CO-197"

    service_date = pd.to_datetime(service_date)
    if str(pa_row["provider_id"]) != str(provider_id):
        return False, "CO-197"

    auth_start = pd.to_datetime(pa_row["auth_start"])
    auth_end = pd.to_datetime(pa_row["auth_end"])
    if pd.isna(auth_start) or pd.isna(auth_end):
        return False, "CO-197"
    if service_date < auth_start or service_date > auth_end:
        return False, "CO-197"

    return True, None


def apply_pricing(
    service_line_id: str,
    billed_amount: float,
    allowed_amount: float,
    config: dict,
) -> dict[str, object]:
    """
    Pricing step (pipeline step 7).

    v1: office_visit flat copay (PR-3); all other lines coinsurance (PR-2);
    contractual write-down (CO-45) when billed exceeds allowed.
    """
    benefits = config["benefits"]
    billed = float(billed_amount)
    allowed = float(allowed_amount)
    contractual = round(max(0.0, billed - allowed), 2)

    if service_line_id == "office_visit":
        copay = float(benefits["office_visit_copay"])
        patient = round(min(copay, allowed), 2)
        patient_carc: str | None = "PR-3"
    else:
        patient = round(
            allowed * float(benefits["default_coinsurance_pct"]), 2
        )
        patient_carc: str | None = "PR-2"

    paid = round(allowed - patient, 2)
    return {
        "contractual_adjustment": contractual,
        "adjustment_carc": "CO-45" if contractual > 0 else None,
        "patient_responsibility": patient,
        "patient_carc": patient_carc,
        "paid_amount": paid,
    }


def adujudicate_claims(
    claims: pd.DataFrame,
    members: pd.DataFrame,
    providers: pd.DataFrame,
    prior_auths: pd.DataFrame,
    config: dict | None = None,
) -> pd.DataFrame:
    cfg = config if config is not None else load_config()
    rng = np.random.default_rng(cfg["seed"])
    pa_by_event = {
        str(row["event_id"]): row for _, row in prior_auths.iterrows()
    }

    adjudicated = claims.copy()
    adjudicated["status"] = pd.NA
    adjudicated["denial_carc"] = pd.NA
    adjudicated["contractual_adjustment"] = pd.NA
    adjudicated["adjustment_carc"] = pd.NA
    adjudicated["patient_responsibility"] = pd.NA
    adjudicated["patient_carc"] = pd.NA
    adjudicated["paid_amount"] = pd.NA

    for row in adjudicated.itertuples(index=True, name="Claim"):

        # enrollment checks
        passed, carc = check_enrollment(members, row.member_id, row.service_date)
        if not passed:
            adjudicated.loc[row.Index, "status"] = "denied"
            adjudicated.loc[row.Index, "denial_carc"] = carc
            continue

        # in-network checks
        passed, carc = check_in_network(providers, row.provider_id)
        if not passed:
            adjudicated.loc[row.Index, "status"] = "denied"
            adjudicated.loc[row.Index, "denial_carc"] = carc
            continue

        # duplicate checks
        passed, carc = check_duplicate(row.is_duplicate)
        if not passed:
            adjudicated.loc[row.Index, "status"] = "denied"
            adjudicated.loc[row.Index, "denial_carc"] = carc
            continue

        # code edit checks
        passed, carc = check_code_edits(providers, row.provider_id, rng)
        if not passed:
            adjudicated.loc[row.Index, "status"] = "denied"
            adjudicated.loc[row.Index, "denial_carc"] = carc
            continue

        pa_row = pa_by_event.get(str(row.event_id))
        passed, carc = check_prior_auth(
            pa_row,
            row.provider_id,
            row.service_date,
            row.pa_required,
        )
        if not passed:
            adjudicated.loc[row.Index, "status"] = "denied"
            adjudicated.loc[row.Index, "denial_carc"] = carc
            continue

        pricing = apply_pricing(
            row.service_line_id,
            row.billed_amount,
            row.allowed_amount,
            cfg,
        )
        for col, val in pricing.items():
            adjudicated.loc[row.Index, col] = val
        adjudicated.loc[row.Index, "status"] = "paid"

    return adjudicated


if __name__ == "__main__":
    cfg = load_config()

    members = generate_members(cfg)
    providers = generate_providers(cfg)
    events = generate_service_events(members, providers, cfg)
    prior_auths = generate_prior_auths(events, providers, cfg)
    claims = generate_claims(events, cfg)

    adjudicated = adujudicate_claims(claims, members, providers, prior_auths, cfg)
