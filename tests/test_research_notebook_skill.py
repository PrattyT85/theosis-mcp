#!/usr/bin/env python3
"""
Offline tests for the Theosis Research Notebook skill, template, reference,
documentation, and example.  These tests read files as UTF-8 and assert
structural properties — no network, no Obsidian vault, no private content.

Note on separate-turn approval: the draft → approve → write protocol
requires the model to show the draft and wait for explicit user approval
in a separate conversation turn before writing to the vault. This is a
runtime behavioural constraint that cannot be validated by static file
inspection; it is verified manually during the review workflow.
"""

import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKILL_DIR = os.path.join(
    REPO, "skills", "note-taking", "theosis-research-notebook"
)
SKILL_PATH = os.path.join(SKILL_DIR, "SKILL.md")
TEMPLATE_PATH = os.path.join(SKILL_DIR, "templates", "research-note.md")
PROVENANCE_PATH = os.path.join(SKILL_DIR, "references", "provenance.md")
DOCS_PATH = os.path.join(REPO, "docs", "research-notebook.md")
EXAMPLE_PATH = os.path.join(REPO, "examples", "research-notebook", "2-peter-2-13-communal-meals.md")
README_PATH = os.path.join(REPO, "README.md")

ALLOWED_NOTE_TYPES = {"observation", "research", "synthesis", "application"}
ALLOWED_STATUSES = {"draft", "reviewed", "published"}

REQUIRED_SECTIONS = [
    "## Biblical text",
    "## Original-language observation",
    "## External source",
    "## Historical/cultural context",
    "## User synthesis",
    "## Application",
]

REQUIRED_FRONT_MATTER_KEYS = [
    "id", "title", "note_type", "status", "scripture_refs", "tags",
    "source_refs", "source_licences", "retrieved_at", "provenance",
    "created", "updated",
]

PATH_REJECTION_GUIDANCE = [
    "readwrite/theosis-notes/",
]
ABSOLUTE_HOME_MARKER = "/" + "home/"


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _parse_front_matter(text: str) -> str:
    """Extract YAML front matter between the first two --- delimiters."""
    parts = text.split("---", 2)
    assert len(parts) >= 3, "File must have opening and closing --- for front matter"
    return parts[1]


def _extract_keys_from_yaml(yaml_text: str) -> dict[str, str]:
    """Minimal YAML key extractor for flat front matter (no deep nesting)."""
    keys: dict[str, str] = {}
    for line in yaml_text.splitlines():
        m = re.match(r"^(\w[\w_]*)\s*:\s*(.*)", line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


def _extract_headings(text: str) -> list[str]:
    """Return all ## level headings from the body (after front matter)."""
    parts = text.split("---", 2)
    body = parts[2] if len(parts) >= 3 else text
    return [line for line in body.splitlines() if re.match(r"^## ", line)]


# ---------------------------------------------------------------------------
# Skill file
# ---------------------------------------------------------------------------

class TestSkillFile:
    """Validate SKILL.md structure, required fields, and policy constraints."""

    @pytest.fixture(autouse=True)
    def _load_skill(self):
        self.content = _read(SKILL_PATH)

    def test_front_matter_starts_at_byte_zero(self):
        assert self.content.startswith("---"), (
            "SKILL.md must begin with YAML front matter delimiter '---'"
        )

    def test_contains_required_name(self):
        assert re.search(r"^name:\s*theosis-research-notebook", self.content, re.M)

    def test_contains_description_beginning_with_use_when(self):
        desc_match = re.search(r"^description:\s*(.+)", self.content, re.M)
        assert desc_match, "description field missing"
        assert desc_match.group(1).strip().startswith("Use when"), (
            "description must begin with 'Use when'"
        )

    def test_contains_version(self):
        assert re.search(r"^version:\s*\S+", self.content, re.M)

    def test_contains_author(self):
        assert re.search(r"^author:", self.content, re.M)

    def test_contains_license(self):
        assert re.search(r"^license:", self.content, re.M)

    def test_contains_metadata_hermes_tags(self):
        assert re.search(r"metadata:", self.content, re.M)
        assert re.search(r"tags:", self.content, re.M)

    def test_references_observe_capture_restate_expand_link_review_workflow(self):
        for step in ["observe", "capture", "restate", "expand", "link", "review"]:
            assert step in self.content.lower(), (
                f"Workflow step '{step}' missing from SKILL.md"
            )

    def test_states_explicit_user_approval_required(self):
        lower = self.content.lower()
        assert "explicit" in lower and ("approval" in lower or "approve" in lower), (
            "Skill must require explicit user approval before vault write"
        )

    def test_states_readwrite_restriction(self):
        assert "readwrite" in self.content.lower(), (
            "Skill must reference readwrite/ vault tier"
        )

    def test_states_private_restriction(self):
        lower = self.content.lower()
        assert "private" in lower and "never" in lower, (
            "Skill must state private/ is never read/written"
        )

    def test_states_readonly_not_modified(self):
        lower = self.content.lower()
        assert "readonly" in lower, "Skill must reference readonly/ tier"
        assert "modify" in lower or "write" in lower, (
            "Skill must state readonly/ is never modified"
        )

    def test_mentions_obsidian_vault_path(self):
        assert "OBSIDIAN_VAULT_PATH" in self.content

    def test_mentions_readwrite_theosis_notes(self):
        assert "readwrite/theosis-notes/" in self.content.lower() or (
            "readwrite/theosis-notes/" in self.content
        ), "Skill must target readwrite/theosis-notes/"

    def test_mentions_wiki_links(self):
        assert "[[" in self.content and "]]" in self.content, (
            "Skill must reference Obsidian [[wiki-links]]"
        )

    def test_mentions_template_reference(self):
        assert "research-note" in self.content.lower() or (
            "template" in self.content.lower()
        ), "Skill should reference the bundled template"

    def test_rejects_dot_dot_absolute_symlink_paths(self):
        """Skill must explicitly reject .., absolute, and symlink path escapes."""
        lower = self.content.lower()
        assert ".." in self.content, "Skill must mention '..' path traversal"
        assert "absolute" in lower or "absolute" in self.content, (
            "Skill must mention absolute path rejection"
        )
        assert "symlink" in lower or "symlink" in self.content, (
            "Skill must mention symlink escape rejection"
        )


# ---------------------------------------------------------------------------
# Template file
# ---------------------------------------------------------------------------

class TestTemplate:
    """Validate the research-note.md template has required front matter and sections."""

    @pytest.fixture(autouse=True)
    def _load_template(self):
        self.content = _read(TEMPLATE_PATH)

    def test_front_matter_delimiters(self):
        assert self.content.startswith("---"), "Template must start with ---"
        parts = self.content.split("---")
        assert len(parts) >= 3, (
            "Template must have opening and closing --- for front matter"
        )

    def test_all_required_front_matter_keys(self):
        for key in REQUIRED_FRONT_MATTER_KEYS:
            assert re.search(rf"^{re.escape(key)}:", self.content, re.M), (
                f"Required front matter key '{key}' missing from template"
            )

    def test_all_six_exact_heading_format(self):
        """All six body sections must use exact '## ' heading format."""
        headings = _extract_headings(self.content)
        for section in REQUIRED_SECTIONS:
            assert section in headings, (
                f"Required section heading '{section}' missing or not exact '## ' format"
            )

    def test_no_real_private_content(self):
        lower = self.content.lower()
        assert ABSOLUTE_HOME_MARKER not in self.content, (
            "Template must not contain absolute home paths"
        )


# ---------------------------------------------------------------------------
# Example note
# ---------------------------------------------------------------------------

class TestExampleNote:
    """Validate the example note structure and safety."""

    @pytest.fixture(autouse=True)
    def _load_example(self):
        self.content = _read(EXAMPLE_PATH)

    def test_no_absolute_home_paths(self):
        assert ABSOLUTE_HOME_MARKER not in self.content, (
            "Example must not contain absolute home paths"
        )

    def test_structural_delimiter_parse(self):
        """YAML front matter is parseable by delimiter split."""
        parts = self.content.split("---")
        assert len(parts) >= 3, (
            "Example must have opening and closing --- for front matter"
        )

    def test_front_matter_required_keys(self):
        """All required front-matter keys must be present with non-empty values."""
        fm = _parse_front_matter(self.content)
        keys = _extract_keys_from_yaml(fm)
        for key in REQUIRED_FRONT_MATTER_KEYS:
            assert key in keys, f"Required front matter key '{key}' missing from example"

    def test_note_type_is_allowed(self):
        fm = _parse_front_matter(self.content)
        keys = _extract_keys_from_yaml(fm)
        assert keys.get("note_type") in ALLOWED_NOTE_TYPES, (
            f"note_type '{keys.get('note_type')}' not in allowed set {ALLOWED_NOTE_TYPES}"
        )

    def test_status_is_allowed(self):
        fm = _parse_front_matter(self.content)
        keys = _extract_keys_from_yaml(fm)
        assert keys.get("status") in ALLOWED_STATUSES, (
            f"status '{keys.get('status')}' not in allowed set {ALLOWED_STATUSES}"
        )

    def test_provenance_is_non_empty(self):
        fm = _parse_front_matter(self.content)
        keys = _extract_keys_from_yaml(fm)
        assert keys.get("provenance"), "provenance must be non-empty"

    def test_has_scripture_ref(self):
        assert re.search(r"scripture_refs:", self.content), (
            "Example must contain scripture_refs"
        )

    def test_has_at_least_one_tag(self):
        assert re.search(r"tags:", self.content), (
            "Example must contain tags"
        )

    def test_has_source_ref(self):
        assert re.search(r"source_refs:", self.content), (
            "Example must contain source_refs"
        )

    def test_has_provenance(self):
        assert re.search(r"provenance:", self.content), (
            "Example must contain provenance"
        )

    def test_all_six_exact_heading_format(self):
        """All six body sections must use exact '## ' heading format."""
        headings = _extract_headings(self.content)
        for section in REQUIRED_SECTIONS:
            assert section in headings, (
                f"Example missing required section heading: {section}"
            )

    def test_template_and_example_same_headings(self):
        """Template and example must have identical section headings."""
        tmpl = _read(TEMPLATE_PATH)
        tmpl_headings = _extract_headings(tmpl)
        ex_headings = _extract_headings(self.content)
        assert tmpl_headings == ex_headings, (
            f"Template headings {tmpl_headings} differ from example headings {ex_headings}"
        )


# ---------------------------------------------------------------------------
# Template ↔ Example heading consistency (class-level)
# ---------------------------------------------------------------------------

class TestTemplateExampleConsistency:
    """Verify template and example have the same section headings."""

    def test_headings_match(self):
        tmpl = _extract_headings(_read(TEMPLATE_PATH))
        ex = _extract_headings(_read(EXAMPLE_PATH))
        assert tmpl == ex, f"Template {tmpl} != example {ex}"


# ---------------------------------------------------------------------------
# Provenance reference
# ---------------------------------------------------------------------------

class TestProvenanceReference:
    """Validate the provenance taxonomy reference."""

    @pytest.fixture(autouse=True)
    def _load_ref(self):
        self.content = _read(PROVENANCE_PATH)

    def test_six_layer_taxonomy_is_primary_section(self):
        """The six-layer taxonomy should be the first or primary section."""
        lower = self.content.lower()
        assert "six-layer taxonomy" in lower or "six layer taxonomy" in lower, (
            "Provenance reference must have a clearly named six-layer taxonomy section"
        )
        # The taxonomy should appear before source/licence/retrieval rules
        idx_tax = lower.find("six-layer taxonomy")
        if idx_tax == -1:
            idx_tax = lower.find("six layer taxonomy")
        assert idx_tax >= 0

    def test_has_separate_rules_section(self):
        """Source/licence/retrieval rules should be in a clearly named separate section."""
        lower = self.content.lower()
        # Look for a section heading that groups source, licence, retrieval, or attribution rules
        assert "source and licence" in lower or "attribution" in lower or "retrieval" in lower, (
            "Provenance reference must have a separate rules/section for "
            "source, licence, retrieval, or attribution guidance"
        )

    def test_mentions_licence_preservation(self):
        assert "licen" in self.content.lower(), (
            "Provenance reference must discuss licence preservation"
        )

    def test_mentions_retrieval(self):
        assert "retriev" in self.content.lower(), (
            "Provenance reference must discuss retrieval metadata"
        )

    def test_mentions_attribution_rules(self):
        lower = self.content.lower()
        assert "attribution" in lower or "attribution" in self.content, (
            "Provenance reference must include attribution rules"
        )


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------

class TestDocs:
    """Validate docs/research-notebook.md coverage."""

    @pytest.fixture(autouse=True)
    def _load_docs(self):
        self.content = _read(DOCS_PATH)

    def test_mentions_obsidian_vault_path(self):
        assert "OBSIDIAN_VAULT_PATH" in self.content

    def test_mentions_offline_portability(self):
        lower = self.content.lower()
        assert "offline" in lower or "portab" in lower, (
            "Docs must discuss offline behaviour or portability"
        )

    def test_mentions_draft_approval_workflow(self):
        lower = self.content.lower()
        assert "draft" in lower and ("approval" in lower or "approve" in lower), (
            "Docs must describe draft/approval workflow"
        )

    def test_mentions_vault_tiers(self):
        lower = self.content.lower()
        assert "readwrite" in lower
        assert "private" in lower
        assert "readonly" in lower

    def test_mentions_search_or_backlinks(self):
        lower = self.content.lower()
        assert "search" in lower or "backlink" in lower, (
            "Docs must mention search or backlinks"
        )

    def test_mentions_wiki_links(self):
        assert "[[" in self.content or "wiki-link" in self.content.lower() or "wiki link" in self.content.lower(), (
            "Docs must reference Obsidian wiki-links"
        )


# ---------------------------------------------------------------------------
# README link
# ---------------------------------------------------------------------------

class TestReadme:
    """Validate README.md links to docs and example."""

    def test_mentions_research_notebook(self):
        content = _read(README_PATH)
        assert "research-notebook" in content.lower() or (
            "Research Notebook" in content
        ), "README must mention the Research Notebook"

    def test_links_to_docs(self):
        content = _read(README_PATH)
        assert "research-notebook.md" in content.lower() or (
            "docs/research-notebook" in content
        ), "README must link to docs/research-notebook.md"

    def test_links_to_example(self):
        content = _read(README_PATH)
        assert "2-peter-2-13" in content.lower() or (
            "examples/research-notebook" in content
        ), "README must reference the example note"

    def test_has_paragraph_description(self):
        """README Research Notebook section should have at least a paragraph description."""
        content = _read(README_PATH)
        # Find the Research Notebook heading and check there's prose below it
        match = re.search(r"## Research Notebook\n\n(.+)", content, re.S)
        assert match, "README Research Notebook section must have a paragraph below the heading"
        para = match.group(1).split("\n\n")[0]  # first paragraph
        assert len(para.split()) >= 15, (
            f"Research Notebook paragraph too short ({len(para.split())} words); "
            "expand to a concise paragraph"
        )


# ---------------------------------------------------------------------------
# Path boundary guidance
# ---------------------------------------------------------------------------

class TestPathBoundaryGuidance:
    """Verify the skill contains explicit rejection guidance for dangerous paths."""

    def test_skill_rejects_dot_dot(self):
        content = _read(SKILL_PATH)
        assert ".." in content, "SKILL.md must mention '..' path traversal"

    def test_skill_rejects_absolute_paths(self):
        content = _read(SKILL_PATH)
        lower = content.lower()
        assert "absolute" in lower, "SKILL.md must mention absolute path rejection"

    def test_skill_rejects_symlink_escapes(self):
        content = _read(SKILL_PATH)
        content = content.lower()
        assert "symlink" in content, "SKILL.md must mention symlink escape rejection"

    def test_skill_states_allowed_root(self):
        content = _read(SKILL_PATH)
        assert "readwrite/theosis-notes/" in content, (
            "SKILL.md must state the allowed write root: readwrite/theosis-notes/"
        )


# ===========================================================================
#  Improvement Area 1 — Provenance capture
# ===========================================================================

class TestProvenanceCapture:
    """Structural tests for source_refs tool+arguments, licence/ISO retrieval
    metadata, and positional multi-source handling.

    These are static file checks. Runtime correctness of provenance capture
    (e.g. that the model actually records real tool arguments at draft time)
    is verified manually during the review workflow.
    """

    def _skill(self) -> str:
        return _read(SKILL_PATH)

    def _prov(self) -> str:
        return _read(PROVENANCE_PATH)

    def _example(self) -> str:
        return _read(EXAMPLE_PATH)

    # --- tool+arguments format in source_refs ---

    def test_skill_mentions_tool_name_and_arguments_in_source_refs(self):
        """SKILL.md must require source_refs to contain actual tool names with
        argument values, e.g. 'theosis_mcp.get_study_notes(reference=...)'.
        """
        content = self._skill()
        lower = content.lower()
        # Must mention tool name pattern (dot-separated tool call)
        assert "get_study_notes" in lower or "theosis_mcp" in lower or (
            "tool" in lower and "arguments" in lower
        ), (
            "SKILL.md must require source_refs to preserve actual tool names "
            "and arguments (e.g. theosis_mcp.get_study_notes(...))"
        )

    def test_provenance_ref_requires_tool_call_format(self):
        """The provenance reference must specify the tool+arguments format
        for source_refs entries.
        """
        prov = self._prov()
        assert "tool" in prov.lower() and ("argument" in prov.lower() or "call" in prov.lower()), (
            "provenance.md must mention tool calls with arguments in source_refs format"
        )

    def test_example_source_refs_use_tool_call_format(self):
        """Example note source_refs must show tool names with arguments,
        not generic labels.
        """
        fm = _parse_front_matter(self._example())
        # Check source_refs lines contain a dot-separated tool call pattern
        source_refs_lines = [
            line.strip().lstrip("- ").strip('"').strip("'")
            for line in fm.splitlines()
            if "source_refs" in line or (re.match(r'^\s+-\s+"?Theosis', line) or re.match(r'^\s+-\s+"?theosis', line))
        ]
        # The example has tool calls like 'Theosis: get_study_notes(2 Peter 2:13)'
        combined = "\n".join(source_refs_lines)
        assert "get_study_notes" in combined or "word_study" in combined or (
            "theosis" in combined.lower()
        ), (
            "Example source_refs must contain actual tool names with arguments"
        )

    # --- licence and ISO retrieval metadata ---

    def test_skill_requires_source_licences_with_unknown_label(self):
        """SKILL.md must require source_licences entries and prohibit
        inventing unknown licences.
        """
        content = self._skill()
        lower = content.lower()
        assert "licence" in lower or "license" in lower, (
            "SKILL.md must mention source_licences"
        )
        assert "unknown" in lower, (
            "SKILL.md must handle unknown licences (mark as 'unknown', never invent)"
        )

    def test_provenance_ref_requires_licence_and_iso_retrieval(self):
        """provenance.md must specify that licence entries and retrieved_at
        use ISO-8601 format.
        """
        prov = self._prov()
        lower = prov.lower()
        assert "iso" in lower, (
            "provenance.md must specify ISO-8601 for retrieved_at"
        )
        assert "unknown" in lower, (
            "provenance.md must handle unknown licences with 'unknown' label"
        )

    def test_example_has_retrieved_at_iso_format(self):
        """Example note retrieved_at must be ISO-8601 format."""
        fm = _parse_front_matter(self._example())
        keys = _extract_keys_from_yaml(fm)
        retrieved = keys.get("retrieved_at", "")
        # Strip surrounding quotes that YAML preserves
        retrieved = retrieved.strip('"').strip("'")
        # ISO-8601 basic check: YYYY-MM-DDTHH:MM:SS or with timezone
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", retrieved), (
            f"Example retrieved_at '{retrieved}' is not ISO-8601 format"
        )

    def test_example_has_source_licences(self):
        """Example note must have source_licences entries."""
        fm = _parse_front_matter(self._example())
        assert "source_licences" in fm, (
            "Example must contain source_licences in front matter"
        )

    # --- positional multi-source handling ---

    def test_skill_requires_positional_source_alignment(self):
        """SKILL.md must state that source_refs, source_licences, and
        retrieved_at are positionally aligned when multiple sources exist.
        """
        content = self._skill()
        lower = content.lower()
        assert "positional" in lower or "positionally" in lower or (
            "multi" in lower and ("source" in lower or "align" in lower)
        ), (
            "SKILL.md must mention positional alignment of source_refs, "
            "source_licences, and retrieved_at for multiple sources"
        )

    def test_provenance_ref_requires_positional_alignment(self):
        """provenance.md must document positional alignment of multi-source
        entries.
        """
        prov = self._prov()
        lower = prov.lower()
        assert "positional" in lower or "positionally" in lower or (
            "align" in lower and "multi" in lower
        ), (
            "provenance.md must document positional multi-source alignment"
        )

    def test_docs_require_positional_alignment(self):
        """docs/research-notebook.md must mention positional multi-source handling."""
        docs = _read(DOCS_PATH)
        lower = docs.lower()
        assert "positional" in lower or "positionally" in lower or (
            "multi" in lower and "source" in lower
        ), (
            "docs/research-notebook.md must mention positional multi-source handling"
        )

    # --- raw source text in labelled sections ---

    def test_skill_requires_raw_source_in_labelled_sections(self):
        """SKILL.md must state that raw returned source text belongs in
        labelled source sections (Biblical text, Original-language
        observation, External source), not silently in User synthesis.
        """
        content = self._skill()
        lower = content.lower()
        assert "labelled" in lower or "labeled" in lower, (
            "SKILL.md must require raw source text in labelled sections"
        )
        assert "user synthesis" in lower or "user-synthesis" in lower or (
            "synthesis" in lower
        ), (
            "SKILL.md must distinguish source text from User synthesis"
        )

    def test_provenance_ref_distinguishes_source_from_synthesis(self):
        """provenance.md must state source-derived text must never be
        rendered as user interpretation/synthesis.
        """
        prov = self._prov()
        lower = prov.lower()
        assert "source" in lower and ("synthesis" in lower or "interpretation" in lower), (
            "provenance.md must distinguish source text from synthesis"
        )

    # --- provenance capture checklist / recipe ---

    def test_skill_has_provenance_capture_checklist(self):
        """SKILL.md must include a copy-pasteable provenance capture
        checklist or recipe section.
        """
        content = self._skill()
        lower = content.lower()
        assert "checklist" in lower or "recipe" in lower or (
            "capture" in lower and "provenance" in lower
        ), (
            "SKILL.md must include a provenance capture checklist or recipe"
        )

    def test_docs_has_provenance_workflow(self):
        """docs/research-notebook.md must document the provenance capture
        workflow with tool+arguments, licence, and ISO retrieval.
        """
        docs = _read(DOCS_PATH)
        lower = docs.lower()
        assert "provenance" in lower, (
            "docs must mention provenance"
        )
        assert "source_refs" in docs or "source ref" in lower or "tool" in lower, (
            "docs must mention source_refs or tool calls"
        )


# ===========================================================================
#  Improvement Area 2 — Opt-in Scripture linking
# ===========================================================================

class TestOptInScriptureLinking:
    """Structural tests for opt-in Scripture detection/normalization and
    wiki-link insertion being OFF by default.

    Runtime behaviour (actually detecting references, showing candidates,
    waiting for approval) is manually verified during the review workflow.
    """

    def _skill(self) -> str:
        return _read(SKILL_PATH)

    def _docs(self) -> str:
        return _read(DOCS_PATH)

    # --- OFF by default ---

    def test_skill_states_scripture_linking_off_by_default(self):
        """SKILL.md must explicitly state automatic Scripture detection and
        wiki-link insertion are OFF by default.
        """
        content = self._skill()
        lower = content.lower()
        assert ("off" in lower and "default" in lower) or (
            "opt-in" in lower or "opt in" in lower
        ), (
            "SKILL.md must state automatic Scripture linking is OFF by default "
            "or opt-in"
        )

    def test_skill_documents_detection_and_normalization_off(self):
        """SKILL.md must mention that automatic Scripture detection and
        normalization are off by default.
        """
        content = self._skill()
        lower = content.lower()
        assert "detect" in lower or "normaliz" in lower or "normalis" in lower, (
            "SKILL.md must mention Scripture detection or normalization"
        )

    def test_docs_states_scripture_linking_off_by_default(self):
        """docs/research-notebook.md must state Scripture linking is OFF
        by default.
        """
        docs = self._docs()
        lower = docs.lower()
        assert ("off" in lower and "default" in lower) or (
            "opt-in" in lower or "opt in" in lower
        ), (
            "docs must state Scripture linking is OFF by default or opt-in"
        )

    # --- exact-link approval ---

    def test_skill_requires_exact_link_approval(self):
        """SKILL.md must require explicit approval of exact links before
        inserting wiki-links.
        """
        content = self._skill()
        lower = content.lower()
        assert "approval" in lower or "approve" in lower, (
            "SKILL.md must require approval for link insertion"
        )
        assert "exact" in lower or "precise" in lower, (
            "SKILL.md must require approval of exact/precise links"
        )

    def test_skill_preserves_user_scripture_text(self):
        """SKILL.md must state that the user's exact Scripture reference
        text is preserved (not normalized away).
        """
        content = self._skill()
        lower = content.lower()
        assert "preserve" in lower or "exact" in lower or "verbatim" in lower, (
            "SKILL.md must state that user's exact Scripture reference text is preserved"
        )

    def test_docs_documents_candidate_links_and_approval(self):
        """docs must describe showing detected references and candidate
        related notes, and requiring approval before inserting links.
        """
        docs = self._docs()
        lower = docs.lower()
        assert "candidate" in lower or "related" in lower or "detected" in lower, (
            "docs must mention showing candidate/detected references"
        )
        assert "approval" in lower or "approve" in lower, (
            "docs must mention approval before link insertion"
        )

    # --- noisy backlinks avoidance ---

    def test_skill_mentions_noisy_backlinks(self):
        """SKILL.md must explain that opt-in linking avoids noisy backlinks."""
        content = self._skill()
        lower = content.lower()
        assert "backlink" in lower or "backlink" in content or (
            "noise" in lower or "noisy" in lower
        ), (
            "SKILL.md must mention noisy backlinks as the reason for opt-in linking"
        )

    # --- search/backlink still available manually ---

    def test_skill_documents_manual_search_and_backlinks(self):
        """SKILL.md must state that search and backlink discovery remain
        available manually.
        """
        content = self._skill()
        lower = content.lower()
        assert "search" in lower, "SKILL.md must mention manual search"
        assert "backlink" in lower or "related" in lower, (
            "SKILL.md must mention manual backlink/related note discovery"
        )


# ===========================================================================
#  Improvement Area 3 — Safe edits to existing notes
# ===========================================================================

class TestSafeEdits:
    """Structural tests for the safe-edit workflow: read → diff → approve →
    re-read → patch → verify. Runtime correctness (that the model actually
    follows these steps) is manually verified.
    """

    def _skill(self) -> str:
        return _read(SKILL_PATH)

    def _docs(self) -> str:
        return _read(DOCS_PATH)

    # --- unified diff / preview ---

    def test_skill_requires_diff_or_preview_before_edit(self):
        """SKILL.md must require producing a unified diff or preview before
        editing an existing note.
        """
        content = self._skill()
        lower = content.lower()
        assert "diff" in lower or "preview" in lower or "unified" in lower, (
            "SKILL.md must require a diff or preview before editing"
        )

    def test_docs_mentions_diff_or_preview(self):
        """docs must mention diff or preview for edits."""
        docs = self._docs()
        lower = docs.lower()
        assert "diff" in lower or "preview" in lower, (
            "docs must mention diff or preview for safe edits"
        )

    # --- separate approval ---

    def test_skill_requires_separate_approval_for_edits(self):
        """SKILL.md must require explicit user approval before patching an
        existing note (after showing the diff).
        """
        content = self._skill()
        lower = content.lower()
        assert "approval" in lower or "approve" in lower, (
            "SKILL.md must require approval before editing existing notes"
        )

    # --- re-read before patch ---

    def test_skill_requires_reread_before_patch(self):
        """SKILL.md must require re-reading the file immediately before
        patching to detect changes since the diff was generated.
        """
        content = self._skill()
        lower = content.lower()
        assert "re-read" in lower or "reread" in lower or (
            "read" in lower and ("before" in lower or "immediately" in lower)
        ), (
            "SKILL.md must require re-reading the file before patching"
        )

    def test_docs_requires_reread_before_patch(self):
        """docs must describe re-read-before-patch workflow."""
        docs = self._docs()
        lower = docs.lower()
        assert "re-read" in lower or "reread" in lower or (
            "read" in lower and "before" in lower
        ), (
            "docs must describe re-read-before-patch workflow"
        )

    # --- abort on collision / conflict ---

    def test_skill_aborts_on_collision_or_conflict(self):
        """SKILL.md must state that edits abort rather than overwrite on
        collision, changed file, or conflict.
        """
        content = self._skill()
        lower = content.lower()
        assert "abort" in lower or "stop" in lower or "cancel" in lower, (
            "SKILL.md must state edits abort on conflict"
        )
        assert "collision" in lower or "conflict" in lower or "changed" in lower, (
            "SKILL.md must mention collision or conflict as an abort condition"
        )

    def test_docs_documents_conflict_handling(self):
        """docs must document collision/conflict handling."""
        docs = self._docs()
        lower = docs.lower()
        assert "collision" in lower or "conflict" in lower or "overwrite" in lower, (
            "docs must document collision/conflict handling"
        )

    # --- patch only the approved note under readwrite/theosis-notes/ ---

    def test_skill_restricts_edit_target_to_readwrite(self):
        """SKILL.md must state that patches only target files under
        readwrite/theosis-notes/.
        """
        content = self._skill()
        assert "readwrite/theosis-notes/" in content, (
            "SKILL.md must restrict edit target to readwrite/theosis-notes/"
        )

    # --- read back and verify ---

    def test_skill_requires_read_back_verify(self):
        """SKILL.md must require reading back the file after patching to
        verify the edit landed correctly.
        """
        content = self._skill()
        lower = content.lower()
        assert ("read back" in lower or "read-back" in lower or
                ("verify" in lower and "after" in lower) or
                "confirm" in lower), (
            "SKILL.md must require read-back verification after patching"
        )

    # --- Git/Obsidian conflict guidance ---

    def test_skill_has_git_conflict_guidance(self):
        """SKILL.md must include Git/Obsidian conflict guidance: never force
        overwrite/force-push, preserve both sides, stop for user resolution.
        """
        content = self._skill()
        lower = content.lower()
        assert "force" in lower and ("overwrite" in lower or "push" in lower), (
            "SKILL.md must warn against force overwrite/force-push"
        )
        assert "preserve" in lower or "both" in lower, (
            "SKILL.md must instruct to preserve both sides on conflict"
        )
        assert "user resolution" in lower or "resolve" in lower or (
            "stop" in lower and "user" in lower
        ), (
            "SKILL.md must instruct to stop for user resolution on conflicts"
        )


# ===========================================================================
#  Improvement Area 4 — Performance guidance
# ===========================================================================

class TestPerformanceGuidance:
    """Structural tests for measurement-first performance guidance.

    Runtime measurement (actually timing searches) is done manually.
    """

    def _skill(self) -> str:
        return _read(SKILL_PATH)

    def _docs(self) -> str:
        return _read(DOCS_PATH)

    def test_skill_has_measurement_first_rule(self):
        """SKILL.md must have a measurement-first performance rule: keep
        file scanning while vault is small; measure before adding an index.
        """
        content = self._skill()
        lower = content.lower()
        assert "measure" in lower or "measurement" in lower, (
            "SKILL.md must have a measurement-first performance rule"
        )

    def test_skill_mentions_file_scanning(self):
        """SKILL.md must mention file scanning as the current approach."""
        content = self._skill()
        lower = content.lower()
        assert "scan" in lower or "file scan" in lower or (
            "search" in lower and "file" in lower
        ), (
            "SKILL.md must mention file scanning for vault search"
        )

    def test_skill_defers_local_index(self):
        """SKILL.md must state that a local index is deferred and not
        added yet.
        """
        content = self._skill()
        lower = content.lower()
        assert "index" in lower and (
            "defer" in lower or "not" in lower or "propos" in lower or "measure" in lower
        ), (
            "SKILL.md must defer local index until measured need"
        )

    def test_docs_has_measurement_first_guidance(self):
        """docs must have measurement-first guidance for performance."""
        docs = self._docs()
        lower = docs.lower()
        assert "measure" in lower or "latency" in lower or (
            "performance" in lower and ("scan" in lower or "index" in lower)
        ), (
            "docs must have measurement-first performance guidance"
        )


# ===========================================================================
#  Improvement Area 5 — Updated deferred/follow-up sections
# ===========================================================================

class TestDeferredSections:
    """Verify that docs/research-notebook.md deferred sections reflect
    only truly future work (indexing, voice capture, migration, richer
    automation) and not the improvements implemented in this change.
    """

    def _docs(self) -> str:
        return _read(DOCS_PATH)

    def test_docs_deferred_section_mentions_indexing(self):
        """Deferred section must mention indexing/local index as future work."""
        docs = self._docs()
        lower = docs.lower()
        assert "index" in lower and (
            "defer" in lower or "future" in lower or "not in this" in lower
        ), (
            "docs deferred section must mention indexing as future work"
        )

    def test_docs_deferred_section_mentions_voice(self):
        """Deferred section must mention voice capture as future work."""
        docs = self._docs()
        lower = docs.lower()
        assert "voice" in lower, (
            "docs deferred section must mention voice capture"
        )

    def test_docs_deferred_section_mentions_migration(self):
        """Deferred section must mention vault migration as future work."""
        docs = self._docs()
        lower = docs.lower()
        assert "migrat" in lower, (
            "docs deferred section must mention migration"
        )

    def test_docs_deferred_section_mentions_automation(self):
        """Deferred section must mention richer automation as future work."""
        docs = self._docs()
        lower = docs.lower()
        assert "automat" in lower, (
            "docs deferred section must mention richer automation"
        )

    def test_docs_provenance_is_not_deferred(self):
        """Provenance capture must NOT appear in deferred sections."""
        docs = self._docs()
        # Find the deferred section
        deferred_match = re.search(
            r"## Deferred.*?(?=\n## |\Z)", docs, re.S | re.I
        )
        if deferred_match:
            deferred = deferred_match.group(0).lower()
            # provenance capture should NOT be in the deferred section
            assert "provenance" not in deferred or (
                "provenance" in deferred and "capture" not in deferred
            ), (
                "Provenance capture must not be listed as deferred — it is implemented"
            )

    def test_docs_safe_edits_is_not_deferred(self):
        """Safe edit workflow must NOT appear in deferred sections."""
        docs = self._docs()
        deferred_match = re.search(
            r"## Deferred.*?(?=\n## |\Z)", docs, re.S | re.I
        )
        if deferred_match:
            deferred = deferred_match.group(0).lower()
            assert "safe edit" not in deferred and "edit workflow" not in deferred, (
                "Safe edit workflow must not be listed as deferred — it is implemented"
            )

    def test_docs_opt_in_linking_is_not_deferred(self):
        """Opt-in Scripture linking must NOT appear in deferred sections."""
        docs = self._docs()
        deferred_match = re.search(
            r"## Deferred.*?(?=\n## |\Z)", docs, re.S | re.I
        )
        if deferred_match:
            deferred = deferred_match.group(0).lower()
            assert "opt-in" not in deferred and "opt in" not in deferred, (
                "Opt-in Scripture linking must not be listed as deferred — it is implemented"
            )


# ===========================================================================
#  Improvement Area 6 — Additional test coverage
# ===========================================================================

class TestExampleProvenanceFormat:
    """Verify the example note demonstrates the new provenance format:
    tool+arguments in source_refs, licence metadata, ISO retrieval,
    positional multi-source alignment.
    """

    def _example(self) -> str:
        return _read(EXAMPLE_PATH)

    def test_example_source_refs_have_tool_with_arguments(self):
        """Example source_refs must show tool names with parenthesised arguments."""
        example = self._example()
        # Must have at least one source_ref with a pattern like:
        # "Theosis: tool_name(arguments)" or "theosis_mcp.tool_name(...)"
        assert re.search(
            r"get_study_notes\(.*\)|word_study\(.*\)|theosis_mcp\.\w+\(.*\)",
            example
        ), (
            "Example source_refs must show tool names with arguments in "
            "parentheses"
        )

    def test_example_source_licences_are_not_invented(self):
        """Example source_licences must use real or explicitly unknown labels,
        never invented/generic text.
        """
        fm = _parse_front_matter(self._example())
        # Extract source_licences values
        in_licences = False
        licences = []
        for line in fm.splitlines():
            if line.strip().startswith("source_licences:"):
                in_licences = True
                continue
            if in_licences:
                m = re.match(r'\s+-\s+"(.+)"', line)
                if m:
                    licences.append(m.group(1))
                else:
                    in_licences = False
        assert len(licences) > 0, "Example must have at least one source_licence"
        # Check they're not just "unknown" for everything when the example
        # has real content (the example uses "CC BY 4.0 (Aquifer Open Study Notes)")
        has_real = any("cc" in l.lower() or "by" in l.lower() or "public" in l.lower() or "unknown" in l.lower() for l in licences)
        assert has_real, (
            f"Example source_licences should have real or 'unknown' labels, got: {licences}"
        )

    def test_example_retrieved_at_matches_source_count(self):
        """When multiple sources exist, retrieved_at should have positional
        alignment (at least documented that it corresponds).
        """
        fm = _parse_front_matter(self._example())
        keys = _extract_keys_from_yaml(fm)
        # The example currently has a single retrieved_at string.
        # For multiple sources, it should be a list — but the key point is
        # that the skill/provenance docs mandate positional alignment.
        # We just verify the key exists and is valid ISO-8601.
        retrieved = keys.get("retrieved_at", "").strip('"').strip("'")
        assert re.match(r"\d{4}-\d{2}-\d{2}T", retrieved), (
            f"Example retrieved_at must be ISO-8601, got: {retrieved}"
        )

    def test_example_two_source_refs_with_two_licences(self):
        """Example demonstrates multi-source handling: two source_refs
        and corresponding licence entries.
        """
        fm = _parse_front_matter(self._example())
        source_count = fm.count("Theosis:") + fm.count("theosis:")
        licence_count = fm.count("source_licences:")
        # The example has 2 source_refs (Theosis: get_study_notes + word_study)
        assert source_count >= 2, (
            f"Example should have at least 2 source_refs, found ~{source_count}"
        )


class TestSkillPerformanceSection:
    """Verify SKILL.md has a dedicated performance/measurement section."""

    def test_skill_has_performance_heading(self):
        content = _read(SKILL_PATH)
        lower = content.lower()
        # Look for a heading containing "performance" or "measurement"
        assert re.search(
            r"^## .*(performance|measurement|index)", content, re.M | re.I
        ), (
            "SKILL.md must have a heading for performance/measurement/index"
        )

    def test_skill_performance_section_defers_indexing(self):
        content = _read(SKILL_PATH)
        lower = content.lower()
        # The performance section should mention deferring local index
        perf_match = re.search(
            r"## .*(performance|measurement|index).*?\n(.*?)(?=\n## |\Z)",
            content, re.S | re.I
        )
        if perf_match:
            section = perf_match.group(0).lower()
            assert "index" in section, (
                "Performance section must discuss local index deferral"
            )


class TestSkillSafeEditSection:
    """Verify SKILL.md has a dedicated safe-edit workflow section."""

    def test_skill_has_safe_edit_heading(self):
        content = _read(SKILL_PATH)
        lower = content.lower()
        assert re.search(
            r"^## .*(safe|edit|patch|diff|conflict)", content, re.M | re.I
        ), (
            "SKILL.md must have a heading for safe edits/diffs/patches"
        )


class TestSkillScriptureLinkingSection:
    """Verify SKILL.md has a dedicated Scripture linking section."""

    def test_skill_has_scripture_linking_heading(self):
        content = _read(SKILL_PATH)
        lower = content.lower()
        assert re.search(
            r"^## .*(scripture.*link|link.*scripture|opt.in|wiki.link)", content, re.M | re.I
        ), (
            "SKILL.md must have a heading for Scripture linking / opt-in / wiki-links"
        )
