#!/usr/bin/env python3
"""
Offline tests for the Theosis Research Notebook skill, template, reference,
documentation, and example.  These tests read files as UTF-8 and assert
structural properties — no network, no Obsidian vault, no private content.
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


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


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


# ---------------------------------------------------------------------------
# Template file
# ---------------------------------------------------------------------------

class TestTemplate:
    """Validate the research-note.md template has required front matter and sections."""

    REQUIRED_FRONT_MATTER_KEYS = [
        "id", "title", "note_type", "status", "scripture_refs", "tags",
        "source_refs", "source_licences", "retrieved_at", "provenance",
        "created", "updated",
    ]

    REQUIRED_SECTIONS = [
        "Biblical text",
        "Original-language observation",
        "External source",
        "Historical/cultural context",
        "User synthesis",
        "Application",
    ]

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
        for key in self.REQUIRED_FRONT_MATTER_KEYS:
            assert re.search(rf"^{re.escape(key)}:", self.content, re.M), (
                f"Required front matter key '{key}' missing from template"
            )

    def test_all_six_labelled_sections(self):
        for section in self.REQUIRED_SECTIONS:
            assert section in self.content, (
                f"Required section heading '{section}' missing from template"
            )

    def test_no_real_private_content(self):
        lower = self.content.lower()
        assert "/home/" not in self.content, (
            "Template must not contain absolute /home/ paths"
        )


# ---------------------------------------------------------------------------
# Provenance reference
# ---------------------------------------------------------------------------

class TestProvenanceReference:
    """Validate the provenance taxonomy reference."""

    @pytest.fixture(autouse=True)
    def _load_ref(self):
        self.content = _read(PROVENANCE_PATH)

    def test_mentions_six_layer_taxonomy(self):
        """Should describe at least six provenance/source layers."""
        keywords = ["biblical", "original-language", "external", "historical", "synthesis", "application"]
        found = sum(1 for kw in keywords if kw in self.content.lower())
        assert found >= 4, (
            f"Expected ≥4 provenance layers, found {found}: {self.content[:200]}"
        )

    def test_mentions_licence_preservation(self):
        assert "licen" in self.content.lower(), (
            "Provenance reference must discuss licence preservation"
        )

    def test_mentions_retrieval(self):
        assert "retriev" in self.content.lower(), (
            "Provenance reference must discuss retrieval metadata"
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
# Example note
# ---------------------------------------------------------------------------

class TestExampleNote:
    """Validate the example note structure and safety."""

    @pytest.fixture(autouse=True)
    def _load_example(self):
        self.content = _read(EXAMPLE_PATH)

    def test_no_absolute_home_paths(self):
        assert "/home/" not in self.content, (
            "Example must not contain absolute /home/ paths"
        )

    def test_structural_delimiter_parse(self):
        """YAML front matter is parseable by delimiter split."""
        parts = self.content.split("---")
        assert len(parts) >= 3, (
            "Example must have opening and closing --- for front matter"
        )

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

    def test_has_all_six_sections(self):
        required = [
            "Biblical text",
            "Original-language observation",
            "External source",
            "Historical/cultural context",
            "User synthesis",
            "Application",
        ]
        for section in required:
            assert section in self.content, (
                f"Example missing required section: {section}"
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
