"""Common source parsing models for Phase 1 M2.

These models carry provenance and source locations only. They do not perform
network access, model calls, Neo4j writes, or incremental synchronization.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Annotated, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceType(StrEnum):
    """Source categories supported by the M2 source adapters."""

    MARKDOWN = "markdown"
    TEXT = "text"
    PDF = "pdf"
    CLASSROOM_CASE = "classroom_case"
    DAILY_RECORD = "daily_record"


class MarkdownLocator(BaseModel):
    """A Markdown section or paragraph location."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["markdown"] = "markdown"
    heading: str | None = None
    heading_level: int | None = Field(default=None, ge=1, le=6)
    paragraph: int | None = Field(default=None, ge=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)

    @field_validator("end_offset")
    @classmethod
    def _offset_order(cls, value: int, info: Any) -> int:
        start = info.data.get("start_offset")
        if start is not None and value < start:
            raise ValueError("end_offset must be greater than or equal to start_offset")
        return value


class TextLocator(BaseModel):
    """A plain-text paragraph and offset location."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["text"] = "text"
    paragraph: int = Field(ge=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)

    @field_validator("end_offset")
    @classmethod
    def _offset_order(cls, value: int, info: Any) -> int:
        start = info.data.get("start_offset")
        if start is not None and value < start:
            raise ValueError("end_offset must be greater than or equal to start_offset")
        return value


class PdfLocator(BaseModel):
    """A location inside a PDF page."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["pdf"] = "pdf"
    page_number: int = Field(ge=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)

    @field_validator("end_offset")
    @classmethod
    def _offset_order(cls, value: int, info: Any) -> int:
        start = info.data.get("start_offset")
        if start is not None and value < start:
            raise ValueError("end_offset must be greater than or equal to start_offset")
        return value


class JsonLocator(BaseModel):
    """A location inside a structured JSON case record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["json"] = "json"
    record_id: str | None = None
    json_pointer: str = ""

    @field_validator("json_pointer")
    @classmethod
    def _validate_pointer(cls, value: str) -> str:
        if value == "":
            return value
        if not value.startswith("/"):
            raise ValueError("JSON Pointer must be empty or start with '/'")
        for token in value[1:].split("/"):
            unescape_json_pointer_token(token)
        return value


Locator = Annotated[
    MarkdownLocator | TextLocator | PdfLocator | JsonLocator,
    Field(discriminator="kind"),
]


class ParsedSection(BaseModel):
    """A text or structured section with a type-specific source locator."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    ordinal: int = Field(ge=0)
    locator: Locator


class ParsedDocument(BaseModel):
    """Source-aware parsed document representation shared by M2 adapters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_type: SourceType
    source_identity: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    content_hash: str
    revision_ref: str | None = None
    parser_version: str = Field(min_length=1)
    title: str | None = None
    sections: tuple[ParsedSection, ...] = ()
    metadata: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="after")
    @classmethod
    def _freeze_metadata(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return cast(Mapping[str, Any], _deep_freeze(value))

    @field_validator("content_hash")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        if len(value) != 64:
            raise ValueError("content_hash must be a 64-character SHA-256 hex digest")
        if any(character not in "0123456789abcdef" for character in value):
            raise ValueError("content_hash must contain lowercase hexadecimal characters")
        return value


def sha256_bytes(content: bytes) -> str:
    """Return the lowercase SHA-256 digest for binary content."""

    return hashlib.sha256(content).hexdigest()


def sha256_text(content: str) -> str:
    """Return the lowercase SHA-256 digest for UTF-8 text."""

    return sha256_bytes(content.encode("utf-8"))


def canonical_source_uri(
    source: str | Path,
    *,
    source_root: str | Path | None = None,
) -> str:
    """Return a stable relative URI for repository files or an explicit URI/path."""

    if isinstance(source, str) and "://" in source:
        return source

    path = Path(source).expanduser()
    if source_root is not None:
        root = Path(source_root).expanduser().resolve()
        resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            raise ValueError(
                "Source path is outside source_root; use an explicit reviewed source URI"
            ) from None
        return PurePosixPath(relative.as_posix()).as_posix()
    if path.is_absolute():
        raise ValueError(
            "Absolute source paths are not portable; pass source_root or an explicit source URI"
        )
    return PurePosixPath(path.as_posix()).as_posix()


def build_source_identity(
    source_type: SourceType | str,
    source_uri: str,
) -> str:
    """Build a stable source identity without invoking Git or external services."""

    kind = SourceType(source_type).value
    canonical_uri = source_uri.strip()
    if not canonical_uri:
        raise ValueError("source_uri must not be empty")
    return f"{kind}:{canonical_uri}"


def source_identity_from_path(
    source_type: SourceType | str,
    path: str | Path,
    *,
    source_root: str | Path | None = None,
) -> str:
    """Build source identity and canonical URI from a local path."""

    uri = canonical_source_uri(path, source_root=source_root)
    return build_source_identity(source_type, uri)


def _deep_freeze(value: Any) -> Any:
    """Recursively copy values into immutable dict/tuple representations."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(_deep_freeze(item) for item in value)
    return value


def escape_json_pointer_token(token: str) -> str:
    """Escape one RFC 6901 JSON Pointer token."""
    return token.replace("~", "~0").replace("/", "~1")


def unescape_json_pointer_token(token: str) -> str:
    """Unescape one RFC 6901 JSON Pointer token."""
    result: list[str] = []
    index = 0
    while index < len(token):
        if token[index] == "~":
            if index + 1 >= len(token) or token[index + 1] not in "01":
                raise ValueError("Invalid RFC 6901 escape in JSON Pointer")
            result.append("~" if token[index + 1] == "0" else "/")
            index += 2
        else:
            result.append(token[index])
            index += 1
    return "".join(result)


def json_pointer(parts: Sequence[str]) -> str:
    """Build an RFC 6901 pointer from decoded token names."""
    if not parts:
        return ""
    return "/" + "/".join(escape_json_pointer_token(part) for part in parts)


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    """Resolve an RFC 6901 pointer against a JSON-compatible value."""
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError("JSON Pointer must be empty or start with '/'")

    current = document
    for encoded_token in pointer[1:].split("/"):
        token = unescape_json_pointer_token(encoded_token)
        if isinstance(current, Mapping):
            if token not in current:
                raise KeyError(token)
            current = current[token]
        elif isinstance(current, (list, tuple)):
            if token == "0":
                position = 0
            elif token.isdigit() and not token.startswith("0"):
                position = int(token)
            else:
                raise KeyError(token)
            if position >= len(current):
                raise KeyError(token)
            current = current[position]
        else:
            raise KeyError(token)
    return current
