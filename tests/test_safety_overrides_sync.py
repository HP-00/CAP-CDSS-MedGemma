"""Test that the committed safety overrides notebook matches the generator output."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATOR = ROOT / "scripts" / "_generate_safety_overrides_notebook.py"
NOTEBOOK = ROOT / "notebooks" / "09_safety_overrides.ipynb"


def _load_generator():
    spec = importlib.util.spec_from_file_location("_generate_safety_overrides_notebook", GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_safety_overrides_notebook_in_sync_with_generator():
    gen = _load_generator()
    expected = gen.render_notebook_text()
    actual = NOTEBOOK.read_text(encoding="utf-8")
    assert actual == expected, (
        "Safety overrides notebook is out of sync. "
        "Run: python3 scripts/_generate_safety_overrides_notebook.py"
    )
