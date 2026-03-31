from __future__ import annotations

import argparse
from pathlib import Path

from .normalizer import NormalizerConfig, normalize_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="normalizador",
        description="Normaliza archivos Excel/CSV de proveedores de informática.",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Archivos o carpetas con .xlsx, .xls y/o .csv",
    )
    parser.add_argument(
        "--mappings",
        default="mappings",
        help="Carpeta con mappings por proveedor (JSON).",
    )
    parser.add_argument(
        "--output",
        default="maestro_normalizado.xlsx",
        help="Archivo Excel de salida.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = NormalizerConfig(
        mappings_dir=Path(args.mappings),
        output_file=Path(args.output),
    )

    productos, errores = normalize_files(args.inputs, config)
    print(
        "Normalización completa:",
        f"{len(productos)} productos válidos,",
        f"{len(errores)} filas en ERRORES.",
        f"Archivo: {config.output_file}",
    )


if __name__ == "__main__":
    main()
