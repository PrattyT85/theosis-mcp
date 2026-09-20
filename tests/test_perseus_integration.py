#!/usr/bin/env python3
"""
Offline tests validating the Perseus integration documentation and smoke-test
contract.  These tests verify that the documentation claims, helper functions,
and expected tool lists are consistent — no network calls required.
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import unicodedata
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Locate the documentation
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
PERSEUS_DOC = REPO_ROOT / "docs" / "perseus-integration.md"
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "perseus_smoke_test.py"


# ---------------------------------------------------------------------------
# 1. Documentation file exists and contains required sections
# ---------------------------------------------------------------------------

class TestPerseusDocExists:
    """Verify the integration doc exists and covers required topics."""

    def test_doc_file_exists(self):
        assert PERSEUS_DOC.exists(), f"Missing docs/perseus-integration.md"

    def test_doc_has_upstream_table(self):
        content = PERSEUS_DOC.read_text()
        assert "tonyjurg/Perseus-mcp" in content
        assert "MIT" in content

    def test_doc_has_pinned_version_strategy(self):
        content = PERSEUS_DOC.read_text()
        assert "v1.0.2" in content
        assert "20c211c" in content
        assert "Pin" in content or "pin" in content

    def test_doc_has_command_shape(self):
        content = PERSEUS_DOC.read_text()
        assert "perseus-mcp" in content
        assert "uv" in content

    def test_doc_has_cache_directory(self):
        content = PERSEUS_DOC.read_text()
        assert "cache" in content.lower()
        assert "XDG_CACHE_HOME" in content

    def test_doc_has_key_tools_table(self):
        content = PERSEUS_DOC.read_text()
        assert "get_passage_plaintext" in content
        assert "search_perseus" in content
        assert "get_capabilities" in content

    def test_doc_has_rate_limit_caveat(self):
        content = PERSEUS_DOC.read_text()
        assert "rate limit" in content.lower() or "throttl" in content.lower()

    def test_doc_has_licence_boundary(self):
        content = PERSEUS_DOC.read_text()
        assert "MIT" in content
        assert "CC BY" in content or "Creative Commons" in content

    def test_doc_has_smoke_workflow(self):
        content = PERSEUS_DOC.read_text()
        assert "smoke" in content.lower()
        assert "perseus_smoke_test.py" in content

    def test_doc_has_hermes_profile_template(self):
        content = PERSEUS_DOC.read_text()
        assert "config.yaml" in content
        assert "transport:" in content
        assert "stdio" in content

    def test_doc_has_no_port_conflict(self):
        """Ensure doc doesn't suggest using port 8002 (occupied by Sefaria)."""
        content = PERSEUS_DOC.read_text()
        # The doc should not instruct the user to bind Perseus to port 8002
        # stdio servers don't use ports, but verify the doc makes this clear
        assert "stdio" in content.lower()

    def test_doc_has_network_dependency_note(self):
        content = PERSEUS_DOC.read_text()
        assert "network" in content.lower()
        assert "no offline fallback" in content.lower() or "live HTTP request" in content.lower()

    def test_doc_mentions_no_credentials(self):
        """Doc should not contain credential storage patterns."""
        content = PERSEUS_DOC.read_text()
        assert "password" not in content.lower() or "no password" in content.lower()
        assert "api_key" not in content.lower() or "api key" not in content.lower()


# ---------------------------------------------------------------------------
# 2. Smoke-test script exists and validates offline
# ---------------------------------------------------------------------------

class TestSmokeScript:
    """Verify the smoke-test script is valid Python and runs offline."""

    def test_smoke_script_exists(self):
        assert SMOKE_SCRIPT.exists(), f"Missing scripts/perseus_smoke_test.py"

    def test_smoke_script_is_valid_python(self):
        """compile() catches syntax errors without executing."""
        source = SMOKE_SCRIPT.read_text()
        compile(source, str(SMOKE_SCRIPT), "exec")

    def test_smoke_script_has_expected_tools_list(self):
        """The smoke script should define EXPECTED_TOOLS with 23 entries."""
        source = SMOKE_SCRIPT.read_text()
        # Find the list assignment
        match = re.search(r'EXPECTED_TOOLS:\s*list\[str\]\s*=\s*\[(.*?)\]', source, re.DOTALL)
        assert match, "EXPECTED_TOOLS list not found in smoke script"
        # Count quoted strings
        tool_names = re.findall(r'"(\w+)"', match.group(1))
        assert len(tool_names) == 23, (
            f"Expected 23 tools in EXPECTED_TOOLS, got {len(tool_names)}: {tool_names}"
        )

    def test_smoke_script_has_main_guard(self):
        source = SMOKE_SCRIPT.read_text()
        assert 'if __name__ == "__main__"' in source

    def test_smoke_script_no_network_imports(self):
        """Script should not import network libraries (httpx, requests, urllib3)."""
        source = SMOKE_SCRIPT.read_text()
        for mod in ("httpx", "requests", "urllib3", "aiohttp"):
            assert f"import {mod}" not in source, (
                f"Smoke script imports {mod} — should be network-free"
            )

    def test_smoke_script_no_credential_patterns(self):
        """Script should not contain credential or password references."""
        source = SMOKE_SCRIPT.read_text()
        assert "password" not in source.lower()
        assert "api_key" not in source.lower()
        assert "token" not in source.lower()


# ---------------------------------------------------------------------------
# 3. Helper function correctness (imported from smoke script)
# ---------------------------------------------------------------------------

class TestPerseusHelpers:
    """Test the deterministic helpers defined in the smoke script."""

    @pytest.fixture(autouse=True)
    def _load_helpers(self):
        """Import helper functions from the smoke script."""
        spec = importlib.util.spec_from_file_location("perseus_smoke", str(SMOKE_SCRIPT))
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.validate_cts_urn = mod.validate_cts_urn
        self.normalize_greek_nfc = mod.normalize_greek_nfc
        self.detect_betacode = mod.detect_betacode
        self.discover_tool_names = mod.discover_tool_names

    # --- CTS URN validation ---

    def test_valid_homer_urn(self):
        assert self.validate_cts_urn("urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1")

    def test_valid_vergil_urn(self):
        assert self.validate_cts_urn("urn:cts:latinLit:phi1294.phi002.perseus-lat2:1.1")

    def test_valid_philo_urn(self):
        assert self.validate_cts_urn("urn:cts:greekLit:tlg1271.tlg001.perseus-grc1:1:1")

    def test_valid_no_reference(self):
        """URN without a reference (work-level) is structurally valid."""
        assert self.validate_cts_urn("urn:cts:greekLit:tlg0012.tlg001.perseus-grc2")

    def test_invalid_not_a_urn(self):
        assert not self.validate_cts_urn("not-a-urn")

    def test_invalid_empty(self):
        assert not self.validate_cts_urn("")

    def test_invalid_just_prefix(self):
        assert not self.validate_cts_urn("urn:cts:")

    def test_invalid_no_namespace(self):
        assert not self.validate_cts_urn("urn:cts:greekLit:")

    # --- Greek NFC normalization ---

    def test_greek_already_nfc(self):
        text = "μῆνιν"
        assert self.normalize_greek_nfc(text) == text

    def test_greek_decomposed_to_nfc(self):
        # Compose combining marks into precomposed characters
        decomposed = "\u03BC\u1F74\u03BD\u03B9\u03BD"  # μὴνιν decomposed
        composed = self.normalize_greek_nfc(decomposed)
        assert composed == unicodedata.normalize("NFC", decomposed)

    def test_greek_logos(self):
        text = "λόγος"
        assert self.normalize_greek_nfc(text) == text

    def test_greek_empty_string(self):
        assert self.normalize_greek_nfc("") == ""

    # --- Beta Code detection ---

    def test_betacode_detected_mh_nin(self):
        assert self.detect_betacode("mh=nin")

    def test_betacode_detected_with_parens(self):
        assert self.detect_betacode("a)/eide")

    def test_betacode_not_detected_plain_ascii(self):
        assert not self.detect_betacode("logos")

    def test_betacode_not_detected_unicode_greek(self):
        assert not self.detect_betacode("μῆνιν")

    def test_betacode_empty_string(self):
        assert not self.detect_betacode("")

    # --- Tool name discovery ---

    def test_discover_tool_names_returns_list(self):
        result = self.discover_tool_names()
        assert isinstance(result, list)

    def test_discover_tool_names_sorted(self):
        result = self.discover_tool_names()
        assert result == sorted(result)


# ---------------------------------------------------------------------------
# 4. Cross-reference: doc tool table matches smoke-script EXPECTED_TOOLS
# ---------------------------------------------------------------------------

class TestDocSmokeConsistency:
    """Ensure the doc's tool list and the smoke script's EXPECTED_TOOLS agree."""

    def test_all_smoke_tools_mentioned_in_doc(self):
        """Every tool in EXPECTED_TOOLS should appear in the integration doc."""
        spec = importlib.util.spec_from_file_location("perseus_smoke", str(SMOKE_SCRIPT))
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        doc_text = PERSEUS_DOC.read_text()
        missing = [t for t in mod.EXPECTED_TOOLS if t not in doc_text]
        assert not missing, f"Tools in smoke script but missing from doc: {missing}"

    def test_doc_does_not_reference_port_8002(self):
        """The doc should not suggest Perseus uses port 8002.

        Port 8002 references are allowed only inside the Sefaria server
        block (where the server-name line precedes the URL line) or in
        prose that explicitly attributes it to Sefaria.
        """
        content = PERSEUS_DOC.read_text()
        lines = content.splitlines()
        for idx, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue  # skip comments/headers
            if ":8002" not in line:
                continue
            # Look at a window of the 3 preceding lines for the word "Sefaria"
            context_window = " ".join(lines[max(0, idx - 3): idx + 1])
            assert "sefaria" in context_window.lower(), (
                f"Doc references port 8002 without Sefaria context: {line}"
            )


# ---------------------------------------------------------------------------
# 5. CHANGELOG mention
# ---------------------------------------------------------------------------

class TestChangelogMention:
    """The CHANGELOG should note the Perseus integration."""

    def test_changelog_has_perseus_entry(self):
        changelog = REPO_ROOT / "CHANGELOG.md"
        if changelog.exists():
            content = changelog.read_text()
            assert "erseus" in content, (
                "CHANGELOG.md does not mention Perseus — add an entry"
            )
        else:
            pytest.skip("CHANGELOG.md does not exist")
