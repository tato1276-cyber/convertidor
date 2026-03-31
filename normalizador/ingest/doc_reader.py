from __future__ import annotations

from pathlib import Path


def read_doc_file(file_path: Path):
    """Placeholder para futuro soporte .doc (requiere conversión/OCR adicional)."""
    raise NotImplementedError(
        f"Formato .doc aún no soportado para {file_path.name}. "
        "Estructura preparada para implementar conversión/OCR en una siguiente etapa."
    )
