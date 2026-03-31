from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd
import pdfplumber


def _clean_cell(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _normalize_table(table: list[list[object]]) -> pd.DataFrame | None:
    if not table:
        return None

    rows = [[_clean_cell(cell) for cell in row] for row in table if row and any(_clean_cell(c) for c in row)]
    if len(rows) < 2:
        return None

    header = rows[0]
    body = rows[1:]
    if not any(header):
        return None

    width = len(header)
    normalized_body = []
    for row in body:
        padded = row + [""] * max(0, width - len(row))
        normalized_body.append(padded[:width])

    return pd.DataFrame(normalized_body, columns=header)


def _split_line_in_columns(line: str) -> list[str] | None:
    line = line.strip()
    if not line:
        return None

    for pattern in [r"\s*\|\s*", r"\s*;\s*", r"\t+"]:
        parts = re.split(pattern, line)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 3:
            return parts

    spaced_parts = re.split(r"\s{2,}", line)
    spaced_parts = [p.strip() for p in spaced_parts if p.strip()]
    if len(spaced_parts) >= 3:
        return spaced_parts

    return None


def _text_to_dataframe(lines: Iterable[str]) -> pd.DataFrame:
    parsed = []
    for line in lines:
        cols = _split_line_in_columns(line)
        if cols:
            parsed.append(cols)

    if len(parsed) < 2:
        raise ValueError("PDF sin tabla interpretable: no se detectaron columnas suficientes.")

    header = parsed[0]
    width = len(header)
    body: list[list[str]] = []
    for row in parsed[1:]:
        if len(row) < width:
            row = row + [""] * (width - len(row))
        body.append(row[:width])

    return pd.DataFrame(body, columns=header)


def read_pdf_file(file_path: Path) -> pd.DataFrame:
    """
    Intenta extraer tablas simples desde PDF.
    Fallback: parsea líneas de texto con separadores comunes.
    """
    extracted_tables: list[pd.DataFrame] = []
    text_lines: list[str] = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                df = _normalize_table(table)
                if df is not None and not df.empty:
                    extracted_tables.append(df)

            page_text = page.extract_text() or ""
            text_lines.extend(page_text.splitlines())

    if extracted_tables:
        return pd.concat(extracted_tables, ignore_index=True)

    return _text_to_dataframe(text_lines)
