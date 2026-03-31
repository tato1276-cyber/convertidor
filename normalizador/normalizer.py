from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .ingest import read_input_file

STANDARD_COLUMNS = [
    "proveedor",
    "archivo_origen",
    "fecha_importacion",
    "codigo_proveedor",
    "sku",
    "descripcion",
    "marca",
    "modelo",
    "categoria",
    "costo_sin_iva",
    "iva_pct",
    "costo_con_iva",
    "stock",
    "estado_stock",
    "moneda",
    "url",
    "observaciones",
]

IMPORTANT_FIELDS = ["codigo_proveedor", "descripcion", "costo_con_iva"]
SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".pdf", ".docx", ".doc"}


@dataclass
class NormalizerConfig:
    mappings_dir: Path = Path("mappings")
    output_file: Path = Path("maestro_normalizado.xlsx")


class ProviderNotDetectedError(Exception):
    pass


def _normalize_col_name(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(name).strip().lower())
    return cleaned


def load_mappings(mappings_dir: Path) -> list[dict[str, Any]]:
    mappings = []
    for file in sorted(mappings_dir.glob("*.json")):
        with file.open("r", encoding="utf-8") as f:
            mapping = json.load(f)
        mapping["_file"] = file.name
        mappings.append(mapping)
    if not mappings:
        raise ValueError(f"No hay mappings JSON en: {mappings_dir}")
    return mappings


def read_supplier_file(file_path: Path) -> pd.DataFrame:
    return read_input_file(file_path)


def detect_provider(file_path: Path, df: pd.DataFrame, mappings: list[dict[str, Any]]) -> dict[str, Any]:
    name = file_path.name.lower()
    normalized_cols = {_normalize_col_name(c) for c in df.columns}

    for mapping in mappings:
        aliases = [a.lower() for a in mapping.get("aliases", [])]
        if any(alias in name for alias in aliases):
            return mapping

    best_match = None
    best_score = -1
    for mapping in mappings:
        source_cols = {_normalize_col_name(c) for c in mapping.get("column_map", {}).keys()}
        required = {_normalize_col_name(c) for c in mapping.get("required_columns", [])}
        overlap = len(normalized_cols & source_cols)
        required_overlap = len(normalized_cols & required)
        score = (required_overlap * 10) + overlap
        if score > best_score:
            best_score = score
            best_match = mapping

    if best_match and best_score > 0:
        return best_match

    raise ProviderNotDetectedError(f"No se pudo detectar proveedor para {file_path.name}")


def clean_text(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def parse_number(value: Any) -> float | None:
    text = clean_text(value)
    if text is None:
        return None
    text = re.sub(r"[^0-9,.-]", "", text)
    if text.count(",") > 0 and text.count(".") > 0:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(",") > 0 and text.count(".") == 0:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def normalize_stock(raw_stock: Any, raw_status: Any = None, rules: dict[str, Any] | None = None) -> tuple[float | None, str]:
    rules = rules or {}
    in_stock_values = {clean_text(v).lower() for v in rules.get("in_stock_values", []) if clean_text(v)}
    out_stock_values = {clean_text(v).lower() for v in rules.get("out_stock_values", []) if clean_text(v)}

    numeric_stock = parse_number(raw_stock)
    if numeric_stock is not None:
        return numeric_stock, "en_stock" if numeric_stock > 0 else "sin_stock"

    candidates = [clean_text(raw_stock), clean_text(raw_status)]
    for item in candidates:
        if not item:
            continue
        token = item.lower()
        if token in in_stock_values:
            return None, "en_stock"
        if token in out_stock_values:
            return None, "sin_stock"
        if "cons" in token:
            return None, "consultar"

    return None, "desconocido"


def normalize_prices(row: dict[str, Any], defaults: dict[str, Any]) -> tuple[float | None, float | None, float | None]:
    iva_pct = parse_number(row.get("iva_pct"))
    if iva_pct is None:
        iva_pct = parse_number(defaults.get("iva_pct"))
    if iva_pct is None:
        iva_pct = 21.0

    costo_sin_iva = parse_number(row.get("costo_sin_iva"))
    costo_con_iva = parse_number(row.get("costo_con_iva"))

    if costo_sin_iva is None and costo_con_iva is not None:
        costo_sin_iva = costo_con_iva / (1 + iva_pct / 100)
    if costo_con_iva is None and costo_sin_iva is not None:
        costo_con_iva = costo_sin_iva * (1 + iva_pct / 100)

    if costo_sin_iva is not None:
        costo_sin_iva = round(costo_sin_iva, 2)
    if costo_con_iva is not None:
        costo_con_iva = round(costo_con_iva, 2)

    return costo_sin_iva, iva_pct, costo_con_iva


def apply_mapping(df: pd.DataFrame, mapping: dict[str, Any], source_file: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    col_map = {k: v for k, v in mapping.get("column_map", {}).items()}
    defaults = mapping.get("defaults", {})
    stock_rules = mapping.get("stock_rules", {})
    provider_name = mapping.get("proveedor", mapping.get("name", "desconocido"))

    normalized_df = pd.DataFrame()
    normalized_lookup = {_normalize_col_name(k): v for k, v in col_map.items()}

    for column in df.columns:
        normalized_source_col = _normalize_col_name(column)
        if normalized_source_col in normalized_lookup:
            normalized_df[normalized_lookup[normalized_source_col]] = df[column]

    for standard_col in STANDARD_COLUMNS:
        if standard_col not in normalized_df.columns:
            default_value = defaults.get(standard_col)
            normalized_df[standard_col] = default_value

    normalized_df["proveedor"] = provider_name
    normalized_df["archivo_origen"] = source_file.name
    normalized_df["fecha_importacion"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    output_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for _, raw_row in normalized_df.iterrows():
        row = {col: clean_text(raw_row.get(col)) for col in STANDARD_COLUMNS}

        costo_sin_iva, iva_pct, costo_con_iva = normalize_prices(row, defaults)
        stock_num, estado_stock = normalize_stock(row.get("stock"), row.get("estado_stock"), stock_rules)

        row["costo_sin_iva"] = costo_sin_iva
        row["iva_pct"] = iva_pct
        row["costo_con_iva"] = costo_con_iva
        row["stock"] = stock_num
        row["estado_stock"] = estado_stock

        for text_col in [
            "codigo_proveedor",
            "sku",
            "descripcion",
            "marca",
            "modelo",
            "categoria",
            "moneda",
            "url",
            "observaciones",
        ]:
            row[text_col] = clean_text(row.get(text_col))

        missing = [field for field in IMPORTANT_FIELDS if not row.get(field)]
        if missing:
            error_row = {**row}
            error_row["motivo_error"] = f"Faltan campos obligatorios: {', '.join(missing)}"
            errors.append(error_row)
            continue

        output_rows.append(row)

    output_df = pd.DataFrame(output_rows, columns=STANDARD_COLUMNS)
    error_df = pd.DataFrame(errors, columns=STANDARD_COLUMNS + ["motivo_error"])
    return output_df, error_df


def collect_input_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for input_path in paths:
        p = Path(input_path)
        if p.is_dir():
            files.extend([f for f in p.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS])
        elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(p)
    unique_files = sorted({f.resolve() for f in files})
    return [Path(f) for f in unique_files]


def normalize_files(input_paths: list[str], config: NormalizerConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    mappings = load_mappings(config.mappings_dir)
    files = collect_input_files(input_paths)

    if not files:
        raise ValueError("No se encontraron archivos .xlsx, .xls, .csv, .pdf, .docx o .doc para procesar.")

    all_products: list[pd.DataFrame] = []
    all_errors: list[pd.DataFrame] = []

    for file_path in files:
        try:
            supplier_df = read_supplier_file(file_path)
            mapping = detect_provider(file_path, supplier_df, mappings)
            products_df, errors_df = apply_mapping(supplier_df, mapping, file_path)
            all_products.append(products_df)
            all_errors.append(errors_df)
        except Exception as exc:
            error = pd.DataFrame(
                [
                    {
                        "proveedor": None,
                        "archivo_origen": file_path.name,
                        "fecha_importacion": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "codigo_proveedor": None,
                        "sku": None,
                        "descripcion": None,
                        "marca": None,
                        "modelo": None,
                        "categoria": None,
                        "costo_sin_iva": None,
                        "iva_pct": None,
                        "costo_con_iva": None,
                        "stock": None,
                        "estado_stock": None,
                        "moneda": None,
                        "url": None,
                        "observaciones": None,
                        "motivo_error": str(exc),
                    }
                ]
            )
            all_errors.append(error)

    productos_final = pd.concat(all_products, ignore_index=True) if all_products else pd.DataFrame(columns=STANDARD_COLUMNS)
    errores_final = (
        pd.concat(all_errors, ignore_index=True)
        if all_errors
        else pd.DataFrame(columns=STANDARD_COLUMNS + ["motivo_error"])
    )

    with pd.ExcelWriter(config.output_file, engine="openpyxl") as writer:
        productos_final.to_excel(writer, sheet_name="PRODUCTOS", index=False)
        errores_final.to_excel(writer, sheet_name="ERRORES", index=False)

    return productos_final, errores_final
