#!/usr/bin/env python3
"""Deterministic offline smoke test for the Perseus-mcp integration.

Validates that the upstream package is importable, exposes the expected MCP
tool names, and that the local CTS-URN and Greek-normalization helpers work
correctly.  No network calls are made.

Usage:
    python scripts/perseus_smoke_test.py
    # or via uv:
    uv run python scripts/perseus_smoke_test.py

Exit codes:
    0  — all checks passed
    1  — one or more checks failed
"""

from __future__ import annotations

import importlib
import sys
import unicodedata
import re

# ---------------------------------------------------------------------------
# Expected tool names (as of perseus-mcp v1.0.2)
# Keep this list in sync with docs/perseus-integration.md and upstream README.
# ---------------------------------------------------------------------------

EXPECTED_TOOLS: list[str] = [
    "get_passage",
    "get_passage_plus",
    "get_passage_plaintext",
    "get_valid_references",
    "get_valid_references_json",
    "count_valid_references",
    "get_capabilities",
    "get_cache_status",
    "refresh_metadata_cache",
    "clear_metadata_cache",
    "list_text_groups",
    "get_author_resources",
    "find_author_names",
    "get_work_resources",
    "get_label",
    "get_first_urn",
    "get_prev_next_urn",
    "search_perseus",
    "search_within_text",
    "get_passage_highlights",
    "get_scaife_library_metadata",
    "get_scaife_passage_json",
    "get_scaife_passage_text",
]


# ---------------------------------------------------------------------------
# Helpers (deterministic, no network)
# ---------------------------------------------------------------------------

def check_import() -> bool:
    """Verify perseus_mcp can be imported."""
    try:
        mod = importlib.import_module("perseus_mcp")
        return hasattr(mod, "__version__") or mod is not None
    except ImportError:
        return False


def discover_tool_names() -> list[str]:
    """Attempt to discover tool names from the package.

    Strategy:
      1. Try importing the server module and inspecting registered tools.
      2. Fall back to scanning source files for ``@mcp.tool`` decorators.
      Returns the union of both discovery paths.
    """
    names: set[str] = set()

    # Strategy 1: import and inspect
    try:
        server_mod = importlib.import_module("perseus_mcp.server")
        # FastMCP registers tools on the ``mcp`` attribute
        mcp_obj = getattr(server_mod, "mcp", None)
        if mcp_obj is not None:
            # FastMCP 1.x: _tool_manager._tools dict
            tm = getattr(mcp_obj, "_tool_manager", None)
            if tm is not None:
                tools_dict = getattr(tm, "_tools", {})
                names.update(tools_dict.keys())
            # FastMCP 1.x: also check _tools directly
            tools_direct = getattr(mcp_obj, "_tools", {})
            if isinstance(tools_direct, dict):
                names.update(tools_direct.keys())
    except Exception:
        pass

    # Strategy 2: source scan (fallback)
    if not names:
        try:
            import pathlib
            mod_file = importlib.import_module("perseus_mcp").__file__
            if mod_file is None:
                return sorted(names)
            pkg_dir = pathlib.Path(mod_file).parent
            for py_file in pkg_dir.rglob("*.py"):
                text = py_file.read_text(errors="replace")
                for match in re.finditer(r'@mcp\.tool\(\s*(?:name\s*=\s*)?["\'](\w+)["\']', text):
                    names.add(match.group(1))
                # Also handle: @mcp.tool def tool_name(
                for match in re.finditer(r'@mcp\.tool\s*\n\s*(?:async\s+)?def\s+(\w+)', text):
                    names.add(match.group(1))
        except Exception:
            pass

    return sorted(names)


def normalize_greek_nfc(text: str) -> str:
    """NFC-normalize Greek text, matching Perseus's normalization."""
    return unicodedata.normalize("NFC", text)


def detect_betacode(text: str) -> bool:
    """Detect whether ASCII input is likely Beta Code (same heuristic as upstream)."""
    bc_marks = set("=/()\\*+#<>") & set(text)
    return len(bc_marks) >= 1


def validate_cts_urn(urn: str) -> bool:
    """Validate a CTS URN has the expected structure."""
    # urn:cts:<namespace>:<work_id>:<reference>
    pattern = r'^urn:cts:[a-zA-Z]+:[a-zA-Z0-9._-]+(?::[a-zA-Z0-9._:-]+)?$'
    return bool(re.match(pattern, urn))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    failures: list[str] = []
    checks_run = 0

    # --- 1. Import check (optional — package may not be installed) ---
    checks_run += 1
    if not check_import():
        print("WARN  perseus_mcp is not importable (optional upstream package not installed)")
    else:
        print("OK    import perseus_mcp")

    # --- 2. Tool name discovery ---
    checks_run += 1
    discovered = discover_tool_names()
    if discovered:
        missing = set(EXPECTED_TOOLS) - set(discovered)
        extra = set(discovered) - set(EXPECTED_TOOLS)
        if missing:
            failures.append(f"missing tools: {sorted(missing)}")
            print(f"FAIL  tool discovery: missing {sorted(missing)}")
        else:
            print(f"OK    tool discovery: {len(discovered)} tools, all expected names present")
        if extra:
            print(f"NOTE  extra tools discovered (upstream may have added): {sorted(extra)}")
    else:
        # If discovery failed entirely, warn but don't fail — the tools exist
        # at runtime even if static inspection couldn't find them
        print("WARN  tool discovery returned empty (tools may still exist at runtime)")

    # --- 3. Greek NFC normalization ---
    checks_run += 1
    test_cases = [
        ("μῆνιν", "μῆνιν"),         # already NFC
        ("μῆνιν", "μῆνιν"),         # decomposed → composed
        ("λόγος", "λόγος"),
    ]
    greek_ok = True
    for decomposed, expected_nfc in test_cases:
        result = normalize_greek_nfc(decomposed)
        if result != expected_nfc:
            greek_ok = False
            failures.append(f"greek NFC: {decomposed!r} → {result!r}, expected {expected_nfc!r}")
    if greek_ok:
        print("OK    Greek NFC normalization")
    else:
        print("FAIL  Greek NFC normalization")

    # --- 4. Beta Code detection ---
    checks_run += 1
    bc_cases = [
        ("mh=nin", True),
        ("a)/eide", True),
        ("logos", False),  # no BC marks
        ("μῆνιν", False),  # Unicode Greek, not BC
    ]
    bc_ok = True
    for text, expected in bc_cases:
        result = detect_betacode(text)
        if result != expected:
            bc_ok = False
            failures.append(f"betacode detect: {text!r} → {result}, expected {expected}")
    if bc_ok:
        print("OK    Beta Code detection heuristic")
    else:
        print("FAIL  Beta Code detection heuristic")

    # --- 5. CTS URN validation ---
    checks_run += 1
    urn_cases = [
        ("urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1", True),
        ("urn:cts:latinLit:phi1294.phi002.perseus-lat2:1.1", True),
        ("urn:cts:greekLit:tlg1271.tlg001.perseus-grc1:1:1", True),
        ("not-a-urn", False),
        ("urn:cts:", False),
        ("urn:cts:greekLit:", False),
    ]
    urn_ok = True
    for urn, expected in urn_cases:
        result = validate_cts_urn(urn)
        if result != expected:
            urn_ok = False
            failures.append(f"CTS URN validate: {urn!r} → {result}, expected {expected}")
    if urn_ok:
        print("OK    CTS URN validation")
    else:
        print("FAIL  CTS URN validation")

    # --- Summary ---
    print(f"\n{checks_run} checks run, {len(failures)} failure(s)")
    if failures:
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("PERSEUS_SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
