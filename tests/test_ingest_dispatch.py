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

    def concat(self, _items, ignore_index=False):
        return FakeDataFrame()


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


def _load_ingest_module():
    fake_pandas = FakePandasModule()

    pkg = ModuleType("normalizador")
    pkg.__path__ = [str(Path("normalizador").resolve())]

    ingest_pkg = ModuleType("normalizador.ingest")
    ingest_pkg.__path__ = [str(Path("normalizador/ingest").resolve())]

    with _PatchModules(
        pandas=fake_pandas,
        normalizador=pkg,
        normalizador__placeholder=ModuleType("normalizador__placeholder"),
        pdfplumber=SimpleNamespace(open=lambda *_args, **_kwargs: None),
        docx=SimpleNamespace(Document=lambda *_args, **_kwargs: None),
    ):
        spec = importlib.util.spec_from_file_location(
            "normalizador.ingest",
            Path("normalizador/ingest/__init__.py"),
            submodule_search_locations=[str(Path("normalizador/ingest").resolve())],
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["normalizador.ingest"] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return module


def test_dispatch_excel_csv_pdf_docx(tmp_path):
    ingest_module = _load_ingest_module()

    cases = {
        "lista.xlsx": ".xlsx",
        "lista.csv": ".csv",
        "lista.pdf": ".pdf",
        "lista.docx": ".docx",
    }

    for filename, ext in cases.items():
        p = tmp_path / filename
        p.write_text("dummy", encoding="utf-8")
        sentinel = object()
        ingest_module.FILE_READERS = {ext: (lambda _p, value=sentinel: value)}
        assert ingest_module.read_input_file(p) is sentinel
