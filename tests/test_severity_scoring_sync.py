"""Test that the committed severity scoring notebook matches the generator output."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATOR = ROOT / "scripts" / "_generate_severity_scoring_notebook.py"
NOTEBOOK = ROOT / "notebooks" / "06_clinical_severity_scoring.ipynb"


def _load_generator():
    spec = importlib.util.spec_from_file_location("_generate_severity_scoring_notebook", GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_severity_scoring_notebook_in_sync_with_generator():
    """Committed severity scoring notebook must match generator output exactly."""
    gen = _load_generator()
    expected = gen.render_notebook_text()
    actual = NOTEBOOK.read_text(encoding="utf-8")
    assert actual == expected, (
        "Severity scoring notebook is out of sync. "
        "Run: python3 scripts/_generate_severity_scoring_notebook.py"
    )
