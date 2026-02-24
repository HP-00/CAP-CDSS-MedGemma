"""Test that the committed contradiction detection notebook matches the generator output."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATOR = ROOT / "scripts" / "_generate_contradiction_detection_notebook.py"
NOTEBOOK = ROOT / "notebooks" / "04_cross_modal_contradictions.ipynb"


def _load_generator():
    spec = importlib.util.spec_from_file_location("_generate_contradiction_detection_notebook", GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_contradiction_detection_notebook_in_sync_with_generator():
    """Committed contradiction detection notebook must match generator output exactly."""
    gen = _load_generator()
    expected = gen.render_notebook_text()
    actual = NOTEBOOK.read_text(encoding="utf-8")
    assert actual == expected, (
        "Contradiction detection notebook is out of sync. "
        "Run: python3 scripts/_generate_contradiction_detection_notebook.py"
    )
