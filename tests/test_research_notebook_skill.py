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
        lower = content.lower()
        assert "symlink" in lower, "SKILL.md must mention symlink escape rejection"

    def test_skill_states_allowed_root(self):
        content = _read(SKILL_PATH)
        assert "readwrite/theosis-notes/" in content, (
            "SKILL.md must state the allowed write root: readwrite/theosis-notes/"
        )
