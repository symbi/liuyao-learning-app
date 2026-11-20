"""Source allowlist configuration.

The importer reads an explicit allowlist. It never scans the user's home
directory and never uploads anything it was not told to.

Safe defaults, all of them:

* ``raw_asr.enabled`` is ``false`` -- low-accuracy transcripts stay out of
  the main chunk/vector/rule pipeline.
* ``daily_records.include`` is ``false`` -- personal daily memos are not
  sent to a model service by default.
* ``external_projects`` is empty -- nothing from another repository is
  imported until the user picks it and confirms the licence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class RawAsrSettings(BaseModel):
    """Source A -- raw transcripts.

    Metadata may be scanned, but content is not read, chunked, embedded
    or sent to a model unless this is explicitly enabled.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    #: Local path to the private raw repository.
    root: Path | None = None
    #: Read transcripts into a separate, low-confidence track.
    index_content: bool = False
    #: Allow transcripts to be sent to the model service.
    allow_model_processing: bool = False


class DailyRecordsSettings(BaseModel):
    """Personal daily casting records."""

    model_config = ConfigDict(extra="forbid")

    include: bool = False
    #: Only import records explicitly marked as classroom cases.
    only_cases: bool = True
    root: Path | None = None


class PdfSettings(BaseModel):
    """Explicitly allowed PDF files."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    #: Paths the user has approved for import.
    files: list[Path] = Field(default_factory=list)
    #: Send PDF text to the model service.
    allow_model_processing: bool = False


class ExternalProject(BaseModel):
    """One approved external repository."""

    model_config = ConfigDict(extra="forbid")

    repo_url: str
    #: Paths inside the repository to import.
    paths: list[str] = Field(default_factory=list)
    #: The commit the import was taken from.
    commit_sha: str | None = None
    author: str | None = None
    license: str | None = None
    license_status: str = "unreviewed"
    #: Source code import is a later sub-phase; Markdown/docs only for now.
    include_source_code: bool = False


class CuratedNotesSettings(BaseModel):
    """Source B -- curated lesson notes. The main chunk source."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    root: Path | None = None
    include_globs: list[str] = Field(default_factory=lambda: ["docs/lessons/*.md"])
    exclude_globs: list[str] = Field(default_factory=list)


class ClassCasesSettings(BaseModel):
    """Classroom cases split out from the lessons."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    root: Path | None = None
    include_globs: list[str] = Field(default_factory=lambda: ["materials/class-cases/**/*.json"])


class SourcesConfig(BaseModel):
    """Top-level source allowlist."""

    model_config = ConfigDict(extra="forbid")

    curated_notes: CuratedNotesSettings = Field(default_factory=CuratedNotesSettings)
    class_cases: ClassCasesSettings = Field(default_factory=ClassCasesSettings)
    raw_asr: RawAsrSettings = Field(default_factory=RawAsrSettings)
    daily_records: DailyRecordsSettings = Field(default_factory=DailyRecordsSettings)
    pdf: PdfSettings = Field(default_factory=PdfSettings)
    external_projects: list[ExternalProject] = Field(default_factory=list)

    def summary(self) -> list[dict[str, Any]]:
        """A safe, human-readable description of what is enabled."""
        rows: list[dict[str, Any]] = [
            {
                "source": "curated_lesson_note",
                "enabled": self.curated_notes.enabled,
                "detail": ", ".join(self.curated_notes.include_globs) or "-",
                "trust": "primary",
            },
            {
                "source": "classroom_case",
                "enabled": self.class_cases.enabled,
                "detail": ", ".join(self.class_cases.include_globs) or "-",
                "trust": "classroom",
            },
            {
                "source": "raw_asr",
                "enabled": self.raw_asr.enabled,
                "detail": (
                    "metadata only"
                    if not self.raw_asr.index_content
                    else "content indexed (low confidence)"
                ),
                "trust": "low_confidence",
            },
            {
                "source": "daily_casting",
                "enabled": self.daily_records.include,
                "detail": "cases only" if self.daily_records.only_cases else "all records",
                "trust": "personal",
            },
            {
                "source": "pdf_reference",
                "enabled": self.pdf.enabled,
                "detail": f"{len(self.pdf.files)} file(s) allowlisted",
                "trust": "external",
            },
            {
                "source": "external_project_doc",
                "enabled": bool(self.external_projects),
                "detail": f"{len(self.external_projects)} project(s)",
                "trust": "external",
            },
        ]
        return rows


def load_sources_config(path: Path) -> SourcesConfig:
    """Load and validate a sources config file.

    Raises on invalid input -- a malformed allowlist must never silently
    widen what gets imported.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Sources config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Sources config must be a mapping: {path}")
    return SourcesConfig.model_validate(data)


def find_sources_config(explicit: Path | None = None) -> Path | None:
    """Locate the sources config, preferring an explicit path."""
    candidates = []
    if explicit is not None:
        candidates.append(explicit)
    else:
        candidates.extend(
            [
                Path.cwd() / "sources.yaml",
                Path.cwd() / "tools" / "liuyao-kb" / "sources.yaml",
            ]
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None
