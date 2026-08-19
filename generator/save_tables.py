"""Write generator DataFrames to data/raw/*.csv for local inspection."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def save_csv(df: pd.DataFrame, name: str) -> Path:
    """Save a table as data/raw/<name>.csv and print the path."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"Wrote {path} ({len(df):,} rows, {len(df.columns)} columns)")
    return path
