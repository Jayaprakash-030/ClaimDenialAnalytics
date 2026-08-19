"""Regenerate all current tables and write them to data/raw/."""

from generator.members import generate_members
from generator.providers import generate_providers
from generator.reference_data import (
    get_carc_codes,
    get_cpt_codes,
    get_icd10_codes,
    get_lines_of_business,
    get_service_lines,
    load_config,
)
from generator.claims import generate_claims
from generator.prior_auth import generate_prior_auths
from generator.save_tables import save_csv
from generator.service_events import generate_service_events


def main() -> None:
    cfg = load_config()

    save_csv(get_lines_of_business(), "lines_of_business")
    save_csv(get_service_lines(), "service_lines")
    save_csv(get_cpt_codes(), "cpt_codes")
    save_csv(get_icd10_codes(), "icd10_codes")
    save_csv(get_carc_codes(), "carc_codes")

    members = generate_members(cfg)
    providers = generate_providers(cfg)
    events = generate_service_events(members, providers, cfg)

    prior_auths = generate_prior_auths(events, providers, cfg)

    claims = generate_claims(events, cfg)

    save_csv(members, "members")
    save_csv(providers, "providers")
    save_csv(events, "service_events")
    save_csv(prior_auths, "prior_auths")
    save_csv(claims, "claims")


if __name__ == "__main__":
    main()
