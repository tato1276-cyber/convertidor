from __future__ import annotations

from pathlib import Path

import pandas as pd


def _read_csv(file_path: Path) -> pd.DataFrame:
    from .csv_reader import read_csv_file

    return read_csv_file(file_path)


def _read_excel(file_path: Path) -> pd.DataFrame:
    from .excel_reader import read_excel_file

    return read_excel_file(file_path)


def _read_pdf(file_path: Path) -> pd.DataFrame:
    try:
        from .pdf_reader import read_pdf_file
    except ImportError as exc:
        raise RuntimeError("Falta dependencia para PDF (pdfplumber).") from exc

    return read_pdf_file(file_path)


def _read_docx(file_path: Path) -> pd.DataFrame:
    try:
        from .docx_reader import read_docx_file
    except ImportError as exc:
        raise RuntimeError("Falta dependencia para DOCX (python-docx).") from exc

    return read_docx_file(file_path)


def _read_doc(file_path: Path) -> pd.DataFrame:
    from .doc_reader import read_doc_file

    return read_doc_file(file_path)


FILE_READERS = {
    ".csv": _read_csv,
    ".xlsx": _read_excel,
    ".xls": _read_excel,
    ".pdf": _read_pdf,
    ".docx": _read_docx,
    ".doc": _read_doc,
}


def read_input_file(file_path: Path) -> pd.DataFrame:
    ext = file_path.suffix.lower()
    reader = FILE_READERS.get(ext)
    if reader is None:
        raise ValueError(f"Formato no soportado: {file_path}")
    return reader(file_path)
