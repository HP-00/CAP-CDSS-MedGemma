"""Benchmark case registry — central access point for all benchmark cases.

Provides get_track2_cases(), get_track1_cases(), and get_all_cases().
The runner at benchmark_data.evaluation.run_benchmark imports get_track2_cases()
from this module when available.
"""

from benchmark_data.cases.group_a_curb65 import GROUP_A_CASES
from benchmark_data.cases.group_b_contradictions import GROUP_B_CASES
from benchmark_data.cases.group_c_stewardship import GROUP_C_CASES
from benchmark_data.cases.track1_cases import TRACK1_CASES


def get_track2_cases() -> list[dict]:
    """Return all Track 2 synthetic cases (33 total)."""
    return GROUP_A_CASES + GROUP_B_CASES + GROUP_C_CASES


def get_track1_cases() -> list[dict]:
    """Return Track 1 RSNA case definitions with placeholder image paths."""
    return TRACK1_CASES


def get_all_cases() -> list[dict]:
    """Return all benchmark cases (Track 1 + Track 2)."""
    return get_track2_cases() + get_track1_cases()
