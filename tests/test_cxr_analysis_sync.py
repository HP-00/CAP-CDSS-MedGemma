"""Test that the committed CXR analysis notebook matches the generator output."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATOR = ROOT / "scripts" / "_generate_cxr_analysis_notebook.py"
NOTEBOOK = ROOT / "notebooks" / "03_cxr_imaging_analysis.ipynb"


def _load_generator():
    spec = importlib.util.spec_from_file_location("_generate_cxr_analysis_notebook", GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cxr_analysis_notebook_in_sync_with_generator():
    """Committed CXR analysis notebook must match generator output exactly."""
    gen = _load_generator()
    expected = gen.render_notebook_text()
    actual = NOTEBOOK.read_text(encoding="utf-8")
    assert actual == expected, (
        "CXR analysis notebook is out of sync with _generate_cxr_analysis_notebook.py. "
        "Run: python3 scripts/_generate_cxr_analysis_notebook.py"
    )
