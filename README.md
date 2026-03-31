# Convertidor / Normalizador de proveedores

Mini app en Python para normalizar archivos de proveedores y consolidarlos en `maestro_normalizado.xlsx`.

## Formatos soportados

- Excel: `.xlsx`, `.xls`
- CSV: `.csv`
- PDF: `.pdf` (texto y tablas simples)
- Word: `.docx` (tablas simples y párrafos delimitados)
- `.doc` antiguo: no implementado aún (se envía a error controlado)

## Estructura

```text
.
├── ejemplos/
├── mappings/
├── normalizador/
├── scripts/
│   └── generar_ejemplos.py
├── streamlit_app.py
├── requirements.txt
└── README.md
```

---

## Guía rápida para **Windows (PowerShell)**

> Ejecutá todos los comandos dentro de la carpeta raíz del proyecto: `convertidor`.

### 1) Crear y activar entorno virtual

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Instalar dependencias

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Generar ejemplos reales (CSV/XLSX/PDF/DOCX)

```powershell
python scripts\generar_ejemplos.py
```

Este script crea/actualiza:
- `ejemplos\proveedor_alpha.csv`
- `ejemplos\proveedor_alpha.xlsx`
- `ejemplos\proveedor_alpha.pdf`
- `ejemplos\proveedor_alpha.docx`

### 4) Probar normalización por CLI

```powershell
python -m normalizador.cli ejemplos --mappings mappings --output maestro_normalizado.xlsx
```

### 5) Comando único de prueba local (simple)

```powershell
python scripts\generar_ejemplos.py; python -m normalizador.cli ejemplos --mappings mappings --output maestro_normalizado.xlsx
```

Si todo sale bien, se genera:
- `maestro_normalizado.xlsx`

con hojas:
- `PRODUCTOS`
- `ERRORES`

---

## Uso opcional con Streamlit

```powershell
streamlit run streamlit_app.py
```

---

## Notas y limitaciones actuales

- PDF y DOCX funcionan mejor con tablas simples o líneas delimitadas (`|`, `;`, tab, múltiples espacios).
- No hay OCR pesado en esta versión.
- `.doc` antiguo queda para una siguiente etapa.
