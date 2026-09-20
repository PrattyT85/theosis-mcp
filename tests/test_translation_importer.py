from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from import_translations import TRANSLATIONS, classify_coverage, parse_rows  # noqa: E402


def test_parse_rows_maps_canonical_and_deuterocanonical_books():
    content = """Book,Chapter,Verse,Text
Genesis,1,1,In the beginning
I Corinthians,1,1,Paul called to be an apostle
Tobit,1,1,The book of the words of Tobit
"""

    rows, books = parse_rows(content)

    assert len(rows) == 3
    assert books["Gen"] == ("Genesis", "Gen", "OT", 1)
    assert books["1Co"] == ("1 Corinthians", "1Co", "NT", 46)
    assert books["Tob"] == ("Tobit", "Tob", "APO", 1000)


def test_historical_editions_have_language_and_licence_metadata():
    assert TRANSLATIONS["WLC"]["language"] == "hbo"
    assert TRANSLATIONS["StatResGNT"]["language"] == "grc"
    assert TRANSLATIONS["Vulgate"]["language"] == "la"
    assert TRANSLATIONS["Peshitta"]["license"] == "Public Domain"


def test_coverage_classification():
    assert classify_coverage(66) == "full"
    assert classify_coverage(78) == "extended"
    assert classify_coverage(27) == "partial"


def test_empty_rows_are_not_imported():
    content = """Book,Chapter,Verse,Text
Genesis,1,1,
Genesis,1,2,Text
"""

    rows, books = parse_rows(content)

    assert len(rows) == 1
    assert set(books) == {"Gen"}
