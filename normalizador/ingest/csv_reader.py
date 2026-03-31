from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_csv_file(file_path: Path) -> pd.DataFrame:
    """Lee CSV intentando autodetectar separador."""
    return pd.read_csv(file_path, dtype=str, encoding="utf-8", sep=None, engine="python")
