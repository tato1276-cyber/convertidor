import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


class FakeDataFrame:
    def __init__(self, data=None, columns=None):
        self.data = data or []
        self.columns = columns or []

    @property
    def empty(self):
        return len(self.data) == 0


class FakePandasModule(ModuleType):
    def __init__(self):
        super().__init__("pandas")
        self.DataFrame = FakeDataFrame

    def concat(self, frames, ignore_index=False):
        data = []
        cols = []
        for frame in frames:
            data.extend(getattr(frame, "data", []))
            cols = getattr(frame, "columns", cols)
        return FakeDataFrame(data=data, columns=cols)


class _PatchModules:
    def __init__(self, **mods):
        self.mods = mods
        self.prev = {}

    def __enter__(self):
        for name, mod in self.mods.items():
            self.prev[name] = sys.modules.get(name)
            sys.modules[name] = mod

    def __exit__(self, exc_type, exc, tb):
        for name, old in self.prev.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


def _load_module(module_name: str, path: str, extra_mods=None):
    fake_pandas = FakePandasModule()
    extra_mods = extra_mods or {}
    patchers = {
        "pandas": fake_pandas,
        **extra_mods,
    }
    with _PatchModules(**patchers):
        spec = importlib.util.spec_from_file_location(module_name, Path(path))
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return module


def test_pdf_text_to_dataframe_fallback():
    pdf_module = _load_module(
        "pdf_reader_test",
        "normalizador/ingest/pdf_reader.py",
        extra_mods={"pdfplumber": SimpleNamespace(open=lambda *_args, **_kwargs: None)},
    )
    df = pdf_module._text_to_dataframe(
        [
            "codigo | descripcion | precio_final",
            "A1 | Notebook 14 | 1000",
            "A2 | Mouse USB | 200",
        ]
    )
    assert df.columns == ["codigo", "descripcion", "precio_final"]
    assert len(df.data) == 2


def test_docx_paragraph_rows_fallback():
    docx_module = _load_module(
        "docx_reader_test",
        "normalizador/ingest/docx_reader.py",
        extra_mods={"docx": SimpleNamespace(Document=lambda *_args, **_kwargs: None)},
    )

    doc = SimpleNamespace(
        paragraphs=[
            SimpleNamespace(text="codigo;descripcion;precio_final"),
            SimpleNamespace(text="B1;Teclado Gamer;500"),
            SimpleNamespace(text="B2;Webcam HD;750"),
        ]
    )
    df = docx_module._extract_paragraph_rows(doc)
    assert df.columns == ["codigo", "descripcion", "precio_final"]
    assert len(df.data) == 2
