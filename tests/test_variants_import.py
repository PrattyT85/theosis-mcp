#!/usr/bin/env python3
"""Tests for VarApp textual variant parser and SBLGNT backward compatibility.

These tests do NOT require PostgreSQL or SWORD modules — they exercise
the pure-Python VarApp parser, the existing SBLGNT parser, and the
witness classification helper.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from import_variants import (
    build_arg_parser,
    main,
    parse_sigla_from_part,
    parse_variant_apparatus,
    parse_varapp_apparatus,
    classify_witness,
    MATTHEW_1_5_IMP,
    MATTHEW_1_1_VARAPP,
)


class TestNoDefaultTruncate(unittest.TestCase):
    """By default the importer must NOT truncate existing data."""

    def test_default_no_truncate_flag(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        self.assertFalse(args.truncate)

    def test_explicit_truncate_flag(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--truncate"])
        self.assertTrue(args.truncate)

    def test_truncate_defaults_to_false_not_none(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        self.assertIsNotNone(args.truncate)
        self.assertFalse(args.truncate)


class TestSiglaParsing(unittest.TestCase):
    """parse_sigla_from_part extracts witness sigla from a text fragment."""

    def test_base_part_wh_niv(self):
        sigla = parse_sigla_from_part("WH NIV")
        self.assertEqual(sigla, ["WH", "NIV"])

    def test_variant_part_treg(self):
        sigla = parse_sigla_from_part("Treg")
        self.assertEqual(sigla, ["Treg"])

    def test_no_sigla(self):
        sigla = parse_sigla_from_part("Βόες … Βόες")
        self.assertEqual(sigla, [])

    def test_known_sigla_set(self):
        for siglum in ("WH", "Treg", "NIV", "RP", "NA", "SBL", "THGNT", "NA28", "UBS5"):
            result = parse_sigla_from_part(siglum)
            self.assertEqual(result, [siglum], f"siglum {siglum!r} not recognised")

    def test_mixed_sigla_and_text(self):
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
        from import_variants import build_witness_payload
        witnesses = build_witness_payload(
            variant_id=1,
            base_sigla=["WH", "WH"],
            var_sigla=["Treg", "Treg"],
        )
        manuscripts = [w["manuscript"] for w in witnesses]
        self.assertEqual(manuscripts, ["WH", "Treg"])

    def test_empty_sigla(self):
        from import_variants import build_witness_payload
        witnesses = build_witness_payload(variant_id=1, base_sigla=[], var_sigla=[])
        self.assertEqual(witnesses, [])


class TestMatthew15Fixture(unittest.TestCase):
    """Parse the documented Matthew 1:5 IMP sample and verify output."""

    def test_parse_matthew_1_5(self):
        entries = parse_variant_apparatus(MATTHEW_1_5_IMP, "SBLGNTApp")
        self.assertGreaterEqual(len(entries), 1, "Should parse at least one entry")

        entry = entries[0]
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


class TestVarAppMatthew11Fixture(unittest.TestCase):
    """Parse the VarApp Matthew 1:1 fixture and verify output.

    Fixture has 3 readings: Δαυὶδ (base), Δαυεὶδ (variant 1), Δαβὶδ (variant 2).
    This produces 2 variant entries — one per non-base reading.
    """

    def test_parse_matthew_1_1(self):
        entries = parse_varapp_apparatus(MATTHEW_1_1_VARAPP)
        self.assertGreaterEqual(len(entries), 2, "Should parse at least 2 variant entries")

        # First variant entry: Δαυεὶδ (paired with base Δαυὶδ)
        entry = entries[0]
        book, chapter, verse, reference, mt_reading, vsource, vreading, base_sigla, var_sigla = entry

        self.assertEqual(book, "Mat")
        self.assertEqual(chapter, 1)
        self.assertEqual(verse, 1)
        self.assertEqual(reference, "Mat 1:1")
        self.assertIn("Δαυὶδ", mt_reading)
        self.assertEqual(vsource, "NT Manuscript Variant Apparatus")

    def test_multiple_readings_create_multiple_entries(self):
        entries = parse_varapp_apparatus(MATTHEW_1_1_VARAPP)
        # 3 readings (1 base + 2 variants) => 2 variant entries
        self.assertEqual(len(entries), 2)

    def test_base_reading(self):
        entries = parse_varapp_apparatus(MATTHEW_1_1_VARAPP)
        entry = entries[0]
        _, _, _, _, _, _, _, base_sigla_str, _ = entry
        self.assertIn("p1", base_sigla_str)
        self.assertIn("Byz", base_sigla_str)

    def test_first_variant_reading(self):
        entries = parse_varapp_apparatus(MATTHEW_1_1_VARAPP)
        entry = entries[0]
        _, _, _, _, _, _, var_reading, _, var_sigla_str = entry
        self.assertIn("Δαυεὶδ", var_reading)
        self.assertIn("B", var_sigla_str)
        self.assertIn("WH", var_sigla_str)

    def test_second_variant_reading(self):
        entries = parse_varapp_apparatus(MATTHEW_1_1_VARAPP)
        entry = entries[1]
        _, _, _, _, _, _, var_reading, _, var_sigla_str = entry
        self.assertIn("Δαβὶδ", var_reading)
        self.assertIn("ς", var_sigla_str)


class TestVarAppEndOfFileFlush(unittest.TestCase):
    """VarApp parser flushes accumulated text at end of file."""

    def test_flush_last_marker(self):
        imp = "$$$Matthew 1:1\nΔαυὶδ] p1 Byz\nΔαυεὶδ] B WH\n"
        entries = parse_varapp_apparatus(imp)
        # 2 readings => 1 variant entry
        self.assertEqual(len(entries), 1)

    def test_single_reading_no_entry(self):
        """Single reading with no variant produces no entries (needs base+variant)."""
        imp = "$$$Matthew 1:1\nΔαυὶδ] p1 Byz\n"
        entries = parse_varapp_apparatus(imp)
        self.assertEqual(len(entries), 0)


class TestVarAppMultipleMarkers(unittest.TestCase):
    """VarApp parser handles multiple verse markers."""

    def test_two_verses(self):
        imp = (
            "$$$Matthew 1:1\n"
            "Δαυὶδ] p1 Byz\n"
            "Δαυεὶδ] B WH\n"
            "$$$Matthew 1:2\n"
            "Ἀβραὰμ] WH\n"
            "Ἀβραὰμ RP\n"
        )
        entries = parse_varapp_apparatus(imp)
        # Each verse has 2 readings => 1 variant entry per verse = 2 total
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0][1], 1)  # chapter
        self.assertEqual(entries[0][2], 1)  # verse
        self.assertEqual(entries[1][1], 1)
        self.assertEqual(entries[1][2], 2)


class TestVarAppWithLbDelimiter(unittest.TestCase):
    """VarApp parser handles <lb/> line-break delimiters between readings."""

    def test_lb_delimiter(self):
        imp = "$$$Matthew 1:1\nΔαυὶδ] p1 Byz<lb/>Δαυεὶδ] B WH\n"
        entries = parse_varapp_apparatus(imp)
        # 2 readings => 1 variant entry
        self.assertEqual(len(entries), 1)
        self.assertIn("Δαυὶδ", entries[0][4])  # base reading
        self.assertIn("Δαυεὶδ", entries[0][6])  # variant reading


class TestClassifyWitness(unittest.TestCase):
    """classify_witness identifies witness type from siglum."""

    def test_papyrus(self):
        self.assertEqual(classify_witness("p1"), "papyrus")
        self.assertEqual(classify_witness("p45"), "papyrus")

    def test_uncial(self):
        self.assertEqual(classify_witness("א"), "uncial")  # aleph
        self.assertEqual(classify_witness("B"), "uncial")

    def test_byzantine(self):
        self.assertEqual(classify_witness("Byz"), "byzantine")
        self.assertEqual(classify_witness("f1"), "byzantine")
        self.assertEqual(classify_witness("f13"), "byzantine")

    def test_edition(self):
        self.assertEqual(classify_witness("WH"), "edition")
        self.assertEqual(classify_witness("NA"), "edition")
        self.assertEqual(classify_witness("UBS"), "edition")
        self.assertEqual(classify_witness("ς"), "edition")

    def test_unknown(self):
        self.assertEqual(classify_witness("xyz123"), "unknown")
        self.assertEqual(classify_witness("foo"), "unknown")


class TestVarAppPreservesUnknownSigla(unittest.TestCase):
    """VarApp parser preserves unknown witness tokens rather than discarding."""

    def test_unknown_siglum_preserved_in_variant(self):
        """Unknown sigla are preserved in variant witness lists."""
        imp = "$$$Matthew 1:1\nΔαυὶδ] p1 Byz\nΔαυεὶδ] p1234\n"
        entries = parse_varapp_apparatus(imp)
        self.assertEqual(len(entries), 1)
        _, _, _, _, _, _, _, base_sigla_str, var_sigla_str = entries[0]
        self.assertIn("p1", base_sigla_str)
        self.assertIn("p1234", var_sigla_str)


class TestVarAppDispatchInMain(unittest.TestCase):
    """Verify main() dispatches to parse_varapp_apparatus for VarApp module."""

    def test_varapp_dispatches_to_varapp_parser(self):
        """main() with --modules VarApp calls parse_varapp_apparatus."""
        import asyncio
        from unittest.mock import AsyncMock, patch, MagicMock
        import tempfile, os

        imp_content = (
            "$$$Matthew 1:1\n"
            "Δαυὶδ] p1 Byz\n"
            "Δαυεὶδ] B WH\n"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create module directory (main() checks os.path.isdir first)
            os.makedirs(os.path.join(tmpdir, "VarApp"), exist_ok=True)
            # Write the IMP file so main() finds it
            imp_file = os.path.join(tmpdir, "VarApp.imp")
            with open(imp_file, "w") as f:
                f.write(imp_content)

            with patch("import_variants.parse_varapp_apparatus") as mock_varapp, \
                 patch("import_variants.parse_variant_apparatus") as mock_sblgnt, \
                 patch("asyncpg.connect", new_callable=AsyncMock) as mock_connect:

                mock_conn = AsyncMock()
                mock_conn.fetchval = AsyncMock(return_value=0)
                mock_conn.close = AsyncMock()
                mock_connect.return_value = mock_conn

                mock_varapp.return_value = []

                # Simulate --modules VarApp --sword-base tmpdir
                sys.argv = ["import_variants.py", "--modules", "VarApp",
                            "--sword-base", tmpdir]

                asyncio.run(main())

                # VarApp parser must have been called, SBLGNT must NOT
                mock_varapp.assert_called_once()
                mock_sblgnt.assert_not_called()

    def test_sblgnt_dispatches_to_sblgnt_parser(self):
        """main() with --modules SBLGNTApp calls parse_variant_apparatus."""
        import asyncio
        from unittest.mock import AsyncMock, patch
        import tempfile, os

        imp_content = "$$$Matthew 1:5\n<item>Βόες … Βόες WH NIV ] Βοὸς … Βοὸς Treg</item>\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "SBLGNTApp"), exist_ok=True)
            imp_file = os.path.join(tmpdir, "SBLGNTApp.imp")
            with open(imp_file, "w") as f:
                f.write(imp_content)

            with patch("import_variants.parse_variant_apparatus") as mock_sblgnt, \
                 patch("import_variants.parse_varapp_apparatus") as mock_varapp, \
                 patch("asyncpg.connect", new_callable=AsyncMock) as mock_connect:

                mock_conn = AsyncMock()
                mock_conn.fetchval = AsyncMock(return_value=0)
                mock_conn.close = AsyncMock()
                mock_connect.return_value = mock_conn

                mock_sblgnt.return_value = []

                sys.argv = ["import_variants.py", "--modules", "SBLGNTApp",
                            "--sword-base", tmpdir]

                asyncio.run(main())

                mock_sblgnt.assert_called_once()
                mock_varapp.assert_not_called()

    def test_varapp_entries_imported_with_correct_source(self):
        """VarApp entries use 'NT Manuscript Variant Apparatus' as source."""
        import asyncio
        from unittest.mock import AsyncMock, patch
        import tempfile, os

        imp_content = (
            "$$$Matthew 1:1\n"
            "Δαυὶδ] p1 Byz\n"
            "Δαυεὶδ] B WH\n"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "VarApp"), exist_ok=True)
            imp_file = os.path.join(tmpdir, "VarApp.imp")
            with open(imp_file, "w") as f:
                f.write(imp_content)

            with patch("import_variants.parse_varapp_apparatus") as mock_varapp, \
                 patch("asyncpg.connect", new_callable=AsyncMock) as mock_connect:

                mock_conn = AsyncMock()
                mock_conn.fetchval = AsyncMock(return_value=0)
                mock_conn.close = AsyncMock()
                mock_connect.return_value = mock_conn

                # Return one entry as the parser would
                mock_varapp.return_value = [
                    ("Mat", 1, 1, "Mat 1:1", "Δαυὶδ",
                     "NT Manuscript Variant Apparatus", "Δαυεὶδ",
                     "p1, Byz", "B, WH")
                ]

                sys.argv = ["import_variants.py", "--modules", "VarApp",
                            "--sword-base", tmpdir]

                asyncio.run(main())

                # Verify insert was called (entries imported)
                self.assertTrue(mock_conn.fetchval.called)
                # The first call is COUNT(*), second is the INSERT
                calls = [str(c) for c in mock_conn.fetchval.call_args_list]
                insert_calls = [c for c in calls if "INSERT" in c]
                self.assertEqual(len(insert_calls), 1)


if __name__ == "__main__":
    unittest.main()
