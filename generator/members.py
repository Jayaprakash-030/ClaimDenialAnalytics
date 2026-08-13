"""Generate synthetic members with enrollment spans.

Enrollment gaps / early terminations (~enrollment_gap_share) seed legitimate
CO-26 / CO-27 eligibility denials later in adjudication — denials must emerge
from these dates, not be rolled independently.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from generator.reference_data import get_lines_of_business, load_config


def _random_date(rng: np.random.Generator, start: date, end: date) -> date:
    """Uniform random date in [start, end] inclusive."""
    days = (end - start).days
    return start + timedelta(days=int(rng.integers(0, days + 1)))


def _enrollment_span(
    rng: np.random.Generator,
    window_start: date,
    window_end: date,
    has_churn: bool,
) -> tuple[date, date | None]:
    """
    Return (enrollment_start, enrollment_end).

    enrollment_end is None when coverage continues through the simulation end
    (still enrolled). When set, it is the last day of coverage.
    """
    if not has_churn:
        # Continuous: most start at/before window; stay through end
        if rng.random() < 0.85:
            enrollment_start = window_start
        else:
            # Mild early joiners within first quarter (still "continuous enough")
            q1_end = window_start + timedelta(days=90)
            enrollment_start = _random_date(rng, window_start, q1_end)
        return enrollment_start, None

    # Churn / gap cohort (~6%): late join, early leave, or both
    mode = rng.choice(["late_join", "early_leave", "both"], p=[0.40, 0.40, 0.20])

    if mode == "late_join":
        # Join after window start → care before start can become CO-26
        enrollment_start = _random_date(
            rng, window_start + timedelta(days=30), window_end - timedelta(days=60)
        )
        enrollment_end = None
    elif mode == "early_leave":
        # Covered from start, leaves mid-window → care after end can become CO-27
        enrollment_start = window_start
        enrollment_end = _random_date(
            rng, window_start + timedelta(days=60), window_end - timedelta(days=30)
        )
    else:
        # Late join and early leave (short spell)
        enrollment_start = _random_date(
            rng, window_start + timedelta(days=30), window_end - timedelta(days=120)
        )
        enrollment_end = _random_date(
            rng, enrollment_start + timedelta(days=30), window_end - timedelta(days=30)
        )

    return enrollment_start, enrollment_end


def generate_members(config: dict | None = None) -> pd.DataFrame:
    """Build the members table with demographics, LOB, and enrollment spans."""
    cfg = config if config is not None else load_config()
    seed = cfg["seed"]
    n = cfg["counts"]["members"]
    gap_share = cfg["rates"]["enrollment_gap_share"]
    window_start = date.fromisoformat(cfg["simulation"]["start_date"])
    window_end = date.fromisoformat(cfg["simulation"]["end_date"])

    rng = np.random.default_rng(seed)
    fake = Faker()
    Faker.seed(seed)

    lobs = get_lines_of_business()
    lob_ids = rng.choice(
        lobs["lob_id"].to_numpy(),
        size=n,
        p=lobs["member_share"].to_numpy(),
    )
    has_churn = rng.random(n) < gap_share

    rows: list[dict] = []
    for i in range(n):
        sex = fake.random_element(elements=("F", "M"))
        first_name = (
            fake.first_name_male() if sex == "M" else fake.first_name_female()
        )
        enrollment_start, enrollment_end = _enrollment_span(
            rng, window_start, window_end, bool(has_churn[i])
        )
        rows.append(
            {
                "member_id": f"M{i + 1:06d}",
                "first_name": first_name,
                "last_name": fake.last_name(),
                "sex": sex,
                "date_of_birth": fake.date_of_birth(minimum_age=0, maximum_age=95),
                "lob_id": lob_ids[i],
                "enrollment_start": enrollment_start,
                "enrollment_end": enrollment_end,
                "has_enrollment_churn": bool(has_churn[i]),
            }
        )

    df = pd.DataFrame(rows)
    df["enrollment_start"] = pd.to_datetime(df["enrollment_start"])
    df["enrollment_end"] = pd.to_datetime(df["enrollment_end"])
    df["date_of_birth"] = pd.to_datetime(df["date_of_birth"])
    return df


def monthly_enrollment_counts(members: pd.DataFrame, config: dict | None = None) -> pd.Series:
    """Count members with active coverage for each month in the simulation window."""
    cfg = config if config is not None else load_config()
    months = pd.period_range(
        start=cfg["simulation"]["start_date"],
        end=cfg["simulation"]["end_date"],
        freq="M",
    )
    counts = {}
    for period in months:
        month_start = period.to_timestamp(how="start")
        month_end = period.to_timestamp(how="end")
        active = (members["enrollment_start"] <= month_end) & (
            members["enrollment_end"].isna() | (members["enrollment_end"] >= month_start)
        )
        counts[str(period)] = int(active.sum())
    return pd.Series(counts, name="enrolled_members")


if __name__ == "__main__":
    cfg = load_config()
    members = generate_members(cfg)

    print(members.head())
    print()
    print("LOB mix:")
    print(members["lob_id"].value_counts(normalize=True).round(3))
    print()
    print(f"Churn cohort share: {members['has_enrollment_churn'].mean():.3f}")
    print(f"Still enrolled (null end): {members['enrollment_end'].isna().mean():.3f}")
    print()
    monthly = monthly_enrollment_counts(members, cfg)
    print("Monthly enrollment (first 6 / last 6):")
    print(monthly.head(6))
    print("...")
    print(monthly.tail(6))
    print(f"Monthly min/max: {monthly.min()} / {monthly.max()}")
