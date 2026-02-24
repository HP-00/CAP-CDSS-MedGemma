"""Tests for LangSmith tracing integration in medgemma.py."""

from cap_agent.models.medgemma import _HAS_LANGSMITH


def test_langsmith_import_flag_exists():
    """Verify the conditional import flag is present."""
    assert isinstance(_HAS_LANGSMITH, bool)


def test_langsmith_detected():
    """langsmith is installed in dev deps, so flag should be True."""
    assert _HAS_LANGSMITH is True


def test_call_medgemma_is_callable():
    """call_medgemma should remain callable regardless of langsmith presence."""
    from cap_agent.models.medgemma import call_medgemma
    assert callable(call_medgemma)
