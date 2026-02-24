"""Test that the committed benchmark notebook matches the generator output."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATOR = ROOT / "scripts" / "_generate_benchmark_evaluation_notebook.py"
NOTEBOOK = ROOT / "notebooks" / "02_benchmark_evaluation.ipynb"


def _load_generator():
    spec = importlib.util.spec_from_file_location("_generate_benchmark_evaluation_notebook", GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_benchmark_notebook_in_sync_with_generator():
    """Committed benchmark notebook must match generator output exactly."""
    gen = _load_generator()
    expected = gen.render_notebook_text()
    actual = NOTEBOOK.read_text(encoding="utf-8")
    assert actual == expected, (
        "Benchmark notebook is out of sync with _generate_benchmark_evaluation_notebook.py. "
        "Run: python3 scripts/_generate_benchmark_evaluation_notebook.py"
    )
