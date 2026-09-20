#!/usr/bin/env python3
"""Tests for manuscript witness importer hardening.

These tests do NOT require PostgreSQL or SWORD modules — they exercise
the pure-Python argument parsing, sigla parsing helper, and the
variant-entry parser against the documented Matthew 1:5 fixture.
"""

import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

# Import the functions we will add to import_variants.py
from import_variants import (
    build_arg_parser,
    parse_sigla_from_part,
    parse_variant_apparatus,
    MATTHEW_1_5_IMP,
)


class TestNoDefaultTruncate(unittest.TestCase):
    """By default the importer must NOT truncate existing data."""

    def test_default_no_truncate_flag(self):
        """--truncate absent means args.truncate is False."""
        parser = build_arg_parser()
        args = parser.parse_args([])
        self.assertFalse(args.truncate)

    def test_explicit_truncate_flag(self):
        """--truncate present means args.truncate is True."""
        parser = build_arg_parser()
        args = parser.parse_args(["--truncate"])
        self.assertTrue(args.truncate)

    def test_truncate_defaults_to_false_not_none(self):
        """Default must be an explicit False, not None."""
        parser = build_arg_parser()
        args = parser.parse_args([])
        self.assertIsNotNone(args.truncate)
        self.assertFalse(args.truncate)


class TestSiglaParsing(unittest.TestCase):
    """parse_sigla_from_part extracts witness sigla from a text fragment."""

    def test_base_part_wh_niv(self):
        """'WH NIV' in the base part should return ('WH', 'NIV')."""
        sigla = parse_sigla_from_part("WH NIV")
        self.assertEqual(sigla, ["WH", "NIV"])

    def test_variant_part_treg(self):
        """'Treg' in the variant part should return ['Treg']."""
        sigla = parse_sigla_from_part("Treg")
        self.assertEqual(sigla, ["Treg"])

    def test_no_sigla(self):
        """Plain Greek text with no known sigla returns empty list."""
        sigla = parse_sigla_from_part("Βόες … Βόες")
        self.assertEqual(sigla, [])

    def test_known_sigla_set(self):
        """All known sigla from the parser are recognised."""
        for siglum in ("WH", "Treg", "NIV", "RP", "NA", "SBL", "THGNT", "NA28", "UBS5"):
            result = parse_sigla_from_part(siglum)
            self.assertEqual(result, [siglum], f"siglum {siglum!r} not recognised")

    def test_mixed_sigla_and_text(self):
        """Text interleaved with sigla: only sigla are extracted."""
        sigla = parse_sigla_from_part("Some words RP and also NA text")
        self.assertEqual(sigla, ["RP", "NA"])


class TestWitnessPayload(unittest.TestCase):
    """build_witness_payload produces correct manuscript_witnesses rows."""

    def test_base_and_variant_witnesses(self):
        from import_variants import build_witness_payload
        witnesses = build_witness_payload(
            variant_id=42,
            base_sigla=["WH", "NIV"],
            var_sigla=["Treg"],
        )
        self.assertEqual(len(witnesses), 3)
        self.assertIn(
            {"variant_id": 42, "manuscript": "WH", "reading_support": "base"},
            witnesses,
        )
        self.assertIn(
            {"variant_id": 42, "manuscript": "NIV", "reading_support": "base"},
            witnesses,
        )
        self.assertIn(
            {"variant_id": 42, "manuscript": "Treg", "reading_support": "variant"},
            witnesses,
        )

    def test_dedup_within_run(self):
        """Duplicate sigla within one call produce only one row per siglum."""
        from import_variants import build_witness_payload
        witnesses = build_witness_payload(
            variant_id=1,
            base_sigla=["WH", "WH"],
            var_sigla=["Treg", "Treg"],
        )
        manuscripts = [w["manuscript"] for w in witnesses]
        self.assertEqual(manuscripts, ["WH", "Treg"])

    def test_empty_sigla(self):
        """No sigla → no witness rows."""
        from import_variants import build_witness_payload
        witnesses = build_witness_payload(variant_id=1, base_sigla=[], var_sigla=[])
        self.assertEqual(witnesses, [])


class TestMatthew15Fixture(unittest.TestCase):
    """Parse the documented Matthew 1:5 IMP sample and verify output."""

    def test_parse_matthew_1_5(self):
        entries = parse_variant_apparatus(MATTHEW_1_5_IMP, "SBLGNTApp")
        self.assertGreaterEqual(len(entries), 1, "Should parse at least one entry")

        entry = entries[0]
        # Tuple layout: (book, chapter, verse, reference, mt_reading,
        #                variant_source, variant_reading, base_sources, var_sources)
        book, chapter, verse, reference, mt_reading, vsource, vreading, base_sigla, var_sigla = entry

        self.assertEqual(book, "Mat")
        self.assertEqual(chapter, 1)
        self.assertEqual(verse, 5)
        self.assertEqual(reference, "Mat 1:5")
        self.assertIn("Βόες", mt_reading)
        self.assertEqual(vsource, "SBLGNT Apparatus")
        self.assertIn("Βοὸς", vreading)
        self.assertIn("WH", base_sigla)
        self.assertIn("NIV", base_sigla)
        self.assertIn("Treg", var_sigla)


if __name__ == "__main__":
    unittest.main()
