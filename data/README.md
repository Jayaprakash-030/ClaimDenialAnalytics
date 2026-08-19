# Local data tables

CSV snapshots of generated / reference tables. Open these when you forget what a Python file produces.

Files in `raw/` are **gitignored** (they can be large). Regenerate anytime:

```bash
uv run python -m generator.dump_tables
```

Or run a single module; its `__main__` also writes its CSV.

| CSV | Produced by | What it is |
|---|---|---|
| `lines_of_business.csv` | `reference_data.py` | 4 LOBs, member share, denial targets, SLA |
| `service_lines.csv` | `reference_data.py` | 7 service lines, volume share, PA flag |
| `cpt_codes.csv` | `reference_data.py` | Real CPT codes by service line |
| `icd10_codes.csv` | `reference_data.py` | Real diagnosis codes |
| `carc_codes.csv` | `reference_data.py` | Denial/adjustment reasons |
| `members.csv` | `members.py` | People + enrollment dates |
| `providers.csv` | `providers.py` | Network, billing quality |
| `service_events.csv` | `service_events.py` | Planned visits (source of truth for PA + claims) |
| `prior_auths.csv` | `prior_auth.py` | PA decisions on PA-required events (approved / denied / never requested) |
