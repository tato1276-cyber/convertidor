from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from normalizador.normalizer import NormalizerConfig, normalize_files

st.set_page_config(page_title="Normalizador de proveedores", layout="wide")
st.title("Normalizador de archivos de proveedores")

uploaded_files = st.file_uploader(
    "Subí archivos .xlsx, .xls o .csv",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True,
)

mappings_dir = st.text_input("Carpeta de mappings", value="mappings")
output_name = st.text_input("Nombre de salida", value="maestro_normalizado.xlsx")

if st.button("Normalizar"):
    if not uploaded_files:
        st.warning("Primero subí al menos un archivo.")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            saved_files: list[str] = []
            for up in uploaded_files:
                target = temp_dir / up.name
                target.write_bytes(up.getvalue())
                saved_files.append(str(target))

            config = NormalizerConfig(
                mappings_dir=Path(mappings_dir),
                output_file=temp_dir / output_name,
            )
            productos, errores = normalize_files(saved_files, config)

            st.success(
                f"Proceso finalizado. Productos: {len(productos)} | Errores: {len(errores)}"
            )
            st.dataframe(productos.head(100), use_container_width=True)
            st.dataframe(errores.head(100), use_container_width=True)

            data = config.output_file.read_bytes()
            st.download_button(
                label="Descargar Excel normalizado",
                data=data,
                file_name=output_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
