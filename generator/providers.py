"""Generate the synthetic payer's provider network.

in_network (~90%) and billing_quality feed later denial / abrasion logic.
A few problem providers are flagged for the Provider Abrasion dashboard.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from faker import Faker

from generator.reference_data import load_config

# (provider_type, specialty, share) — shares must sum to 1.0
_PROVIDER_MIX: list[tuple[str, str, float]] = [
    ("independent_physician", "primary_care", 0.25),
    ("independent_physician", "cardiology", 0.05),
    ("independent_physician", "orthopedics", 0.05),
    ("ambulatory_clinic", "primary_care", 0.15),
    ("ambulatory_clinic", "multi_specialty", 0.05),
    ("imaging_center", "radiology", 0.10),
    ("lab", "pathology", 0.10),
    ("hospital", "general_acute", 0.10),
    ("hospital", "surgery", 0.05),
    ("pt_clinic", "physical_therapy", 0.10),
]

_FACILITY_POOL = [
    "Northside Health System",
    "Riverbend Medical Group",
    "Summit Care Network",
    "Lakeshore Physicians",
    "Independent / Unaffiliated",
]

_PROBLEM_PROVIDER_COUNT = 3


def generate_providers(config: dict | None = None) -> pd.DataFrame:
    """Build the providers table with network status and billing quality."""
    cfg = config if config is not None else load_config()
    seed = cfg["seed"]
    n = cfg["counts"]["providers"]
    in_network_share = cfg["rates"]["in_network_share"]

    rng = np.random.default_rng(seed)
    fake = Faker()
    Faker.seed(seed)

    types = [t for t, _, _ in _PROVIDER_MIX]
    specialties = [s for _, s, _ in _PROVIDER_MIX]
    weights = np.array([w for _, _, w in _PROVIDER_MIX], dtype=float)
    weights = weights / weights.sum()

    mix_idx = rng.choice(len(_PROVIDER_MIX), size=n, p=weights)
    in_network = rng.random(n) < in_network_share

    # Most providers: billing_quality ~ Beta skewed high; problem ones forced low later
    billing_quality = np.clip(rng.beta(5, 1.5, size=n), 0.15, 1.0)

    problem_idx = set(rng.choice(n, size=_PROBLEM_PROVIDER_COUNT, replace=False).tolist())

    rows: list[dict] = []
    for i in range(n):
        is_problem = i in problem_idx
        quality = float(billing_quality[i])
        if is_problem:
            quality = float(rng.uniform(0.10, 0.35))

        provider_type = types[mix_idx[i]]
        specialty = specialties[mix_idx[i]]

        if provider_type in {"independent_physician", "ambulatory_clinic", "pt_clinic"}:
            name = f"Dr. {fake.last_name()}" if provider_type == "independent_physician" else fake.company()
        elif provider_type == "hospital":
            name = f"{fake.city()} {rng.choice(['Medical Center', 'Hospital', 'Regional Hospital'])}"
        elif provider_type == "imaging_center":
            name = f"{fake.last_name()} Imaging"
        else:
            name = f"{fake.last_name()} Laboratory"

        rows.append(
            {
                "provider_id": f"P{i + 1:06d}",
                "provider_name": name,
                "provider_type": provider_type,
                "specialty": specialty,
                "facility_name": str(rng.choice(_FACILITY_POOL)),
                "npi": f"{rng.integers(1000000000, 9999999999)}",
                "in_network": bool(in_network[i]),
                "billing_quality": round(quality, 3),
                "is_problem_provider": is_problem,
            }
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    cfg = load_config()
    providers = generate_providers(cfg)

    print(providers.head())
    print()
    print(f"Count: {len(providers)} (target {cfg['counts']['providers']})")
    print(f"In-network share: {providers['in_network'].mean():.3f} (target {cfg['rates']['in_network_share']})")
    print()
    print("Provider type mix:")
    print(providers["provider_type"].value_counts(normalize=True).round(3))
    print()
    print("Specialty mix:")
    print(providers["specialty"].value_counts(normalize=True).round(3))
    print()
    problems = providers.loc[providers["is_problem_provider"]]
    print(f"Problem providers: {len(problems)}")
    print(problems[["provider_id", "provider_name", "billing_quality", "in_network"]].to_string(index=False))
    print()
    print(f"Billing quality mean (all): {providers['billing_quality'].mean():.3f}")
    print(f"Billing quality mean (problems): {problems['billing_quality'].mean():.3f}")
