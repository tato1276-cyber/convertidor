from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_excel_file(file_path: Path) -> pd.DataFrame:
    """Lee archivos .xlsx y .xls manteniendo compatibilidad con el flujo existente."""
    return pd.read_excel(file_path, dtype=str)
