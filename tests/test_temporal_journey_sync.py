"""Test that the committed temporal journey notebook matches the generator output."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATOR = ROOT / "scripts" / "_generate_temporal_journey_notebook.py"
NOTEBOOK = ROOT / "notebooks" / "07_temporal_patient_journey.ipynb"


def _load_generator():
    spec = importlib.util.spec_from_file_location("_generate_temporal_journey_notebook", GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_temporal_journey_notebook_in_sync_with_generator():
    gen = _load_generator()
    expected = gen.render_notebook_text()
    actual = NOTEBOOK.read_text(encoding="utf-8")
    assert actual == expected, (
        "Temporal journey notebook is out of sync. "
        "Run: python3 scripts/_generate_temporal_journey_notebook.py"
    )
