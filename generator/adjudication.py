"""Adjudicate submitted claims through the payer pipeline (first-fail-wins)."""

from __future__ import annotations

import pandas as pd

from generator.claims import generate_claims
from generator.members import generate_members
from generator.prior_auth import generate_prior_auths
from generator.providers import generate_providers
from generator.reference_data import load_config
from generator.service_events import generate_service_events


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


def adujudicate_claims(
    claims: pd.DataFrame, members: pd.DataFrame, providers: pd.DataFrame
) -> pd.DataFrame:
    adjudicated = claims.copy()
    adjudicated["status"] = pd.NA
    adjudicated["denial_carc"] = pd.NA

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

    return adjudicated


if __name__ == "__main__":
    cfg = load_config()

    members = generate_members(cfg)
    providers = generate_providers(cfg)
    events = generate_service_events(members, providers, cfg)
    prior_auths = generate_prior_auths(events, providers, cfg)
    claims = generate_claims(events, cfg)

    adjudicated = adujudicate_claims(claims, members, providers)
