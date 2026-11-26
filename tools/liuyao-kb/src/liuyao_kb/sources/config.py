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

from pathlib import Path, PurePosixPath
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class AllowedDailyRecord(BaseModel):
    """One daily-record subrecord the user has explicitly allowlisted.

    The pair (``path``, ``record_id``) is the whole grant: ``path`` is the
    repository-relative POSIX path of a daily-records JSON container and
    ``record_id`` is the ``id`` of one ``additionalQuestions[]`` subrecord
    inside it. Classification flags on the record itself (``isCase``,
    ``caseSource``) never substitute for this explicit entry.
    """

    model_config = ConfigDict(extra="forbid")

    path: str
    record_id: str

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        raw = value.strip().replace("\\", "/")
        if not raw or raw.startswith("/") or ":" in raw.split("/")[0]:
            raise ValueError("allowed record path must be a repository-relative POSIX path")
        segments: list[str] = []
        for segment in raw.split("/"):
            if segment in {"", "."}:
                continue
            if segment == "..":
                raise ValueError("allowed record path must not contain '..' segments")
            segments.append(segment)
        if not segments:
            raise ValueError("allowed record path must not be empty")
        return PurePosixPath(*segments).as_posix()

    @field_validator("record_id")
    @classmethod
    def _validate_record_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("allowed record_id must not be empty")
        return stripped


class DailyRecordsSettings(BaseModel):
    """Personal daily casting records.

    Fail-closed: ``include`` defaults to ``False``, and even with
    ``include`` on, only subrecords named in ``allowed_records`` are
    eligible. ``only_cases`` (default ``True``) additionally requires an
    allowlisted subrecord to be explicitly marked ``isCase: true``
    before it is mapped; it never widens the allowlist and is never a
    substitute for explicit (path, record_id) entries.
    """

    model_config = ConfigDict(extra="forbid")

    include: bool = False
    #: Only import records explicitly marked as classroom cases.
    only_cases: bool = True
    root: Path | None = None
    #: Exact (container path, subrecord id) pairs the user has approved.
    allowed_records: list[AllowedDailyRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_allowlist(self) -> DailyRecordsSettings:
        seen_pairs: set[tuple[str, str]] = set()
        paths_by_id: dict[str, str] = {}
        for entry in self.allowed_records:
            pair = (entry.path, entry.record_id)
            if pair in seen_pairs:
                raise ValueError(
                    f"duplicate allowed_records entry: {entry.path} / {entry.record_id}"
                )
            seen_pairs.add(pair)
            other_path = paths_by_id.setdefault(entry.record_id, entry.path)
            if other_path != entry.path:
                raise ValueError(
                    f"record_id {entry.record_id} is allowlisted under two different "
                    f"paths: {other_path} and {entry.path}"
                )
        return self

    def allowed_ids_for(self, relative_path: str) -> tuple[str, ...]:
        """Return the allowlisted subrecord ids for one container path."""
        normalized = relative_path.strip().replace("\\", "/")
        segments = [s for s in normalized.split("/") if s not in {"", "."}]
        canonical = PurePosixPath(*segments).as_posix() if segments else ""
        return tuple(entry.record_id for entry in self.allowed_records if entry.path == canonical)


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


class CaseReferenceSection(BaseModel):
    """One notes section assigned to a case, with its role."""

    model_config = ConfigDict(extra="forbid")

    #: Matched against the start of a chunk's heading_path entries,
    #: for example "7. " for the seventh numbered section.
    heading_prefix: str = Field(min_length=1)
    role: Literal["primary", "secondary"] = "primary"


class CaseReferenceSettings(BaseModel):
    """One explicit ClassCase -> lesson-notes REFERENCES assignment.

    References are never inferred from content similarity: a human
    records here which sections of which notes document a case's
    REFERENCES links point at. ``notes_path`` is the
    repository-relative POSIX path of the notes Markdown; the
    importer composes its document_id from the repository slug.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    notes_path: str
    sections: list[CaseReferenceSection] = Field(min_length=1)

    @field_validator("notes_path")
    @classmethod
    def _validate_notes_path(cls, value: str) -> str:
        raw = value.strip().replace("\\", "/")
        if not raw or raw.startswith("/") or ":" in raw.split("/")[0]:
            raise ValueError("notes_path must be a repository-relative POSIX path")
        segments: list[str] = []
        for segment in raw.split("/"):
            if segment in {"", "."}:
                continue
            if segment == "..":
                raise ValueError("notes_path must not contain '..' segments")
            segments.append(segment)
        if not segments:
            raise ValueError("notes_path must not be empty")
        return PurePosixPath(*segments).as_posix()


class SourcesConfig(BaseModel):
    """Top-level source allowlist."""

    model_config = ConfigDict(extra="forbid")

    curated_notes: CuratedNotesSettings = Field(default_factory=CuratedNotesSettings)
    class_cases: ClassCasesSettings = Field(default_factory=ClassCasesSettings)
    raw_asr: RawAsrSettings = Field(default_factory=RawAsrSettings)
    daily_records: DailyRecordsSettings = Field(default_factory=DailyRecordsSettings)
    pdf: PdfSettings = Field(default_factory=PdfSettings)
    external_projects: list[ExternalProject] = Field(default_factory=list)
    #: Explicit case -> notes REFERENCES assignments (M4b). Empty by
    #: default: no references are created unless a human lists them.
    case_references: list[CaseReferenceSettings] = Field(default_factory=list)

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
            {
                "source": "case_references",
                "enabled": bool(self.case_references),
                "detail": f"{len(self.case_references)} explicit case assignment(s)",
                "trust": "classroom",
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
