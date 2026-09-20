from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from backfill_manuscript_witnesses import split_sigla, witness_rows  # noqa: E402


def test_split_sigla_filters_unknown_and_deduplicates():
    assert split_sigla("WH, NIV; Treg unknown WH") == ["WH", "NIV", "Treg"]


def test_witness_rows_maps_support_and_deduplicates():
    rows = witness_rows([(7, "WH, WH", "Treg; Treg")])
    assert rows == [(7, "WH", "base"), (7, "Treg", "variant")]


def test_witness_rows_handles_empty_fields():
    assert witness_rows([(7, None, "")]) == []
