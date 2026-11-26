"""Stable ID formulas for the Phase 1 knowledge base (plan section 8).

M3 defines these formulas; the M4 importer computes actual IDs when
it scans sources, hashes content and cuts chunks. The formulas are
pure composition over validated components, joined with ``|`` (a
character that cannot appear in a source-type token, a repository
slug, or a normalized repository-relative path), so every ID stays
human-readable and unambiguous:

* ``document_id = source_type + repository + path`` — the stable
  identity of one source file.
* ``revision_id = document_id + content_hash`` — one version of that
  file; ``content_hash`` is the SHA-256 of the original bytes, the
  same digest rule the M2 source adapters already use.
* ``chunk_id = document_id + chunker_version + paragraph_ordinal
  + subchunk_index + chunk_text_hash`` — one chunk of one document
  (composition revised in M4a; see :func:`make_chunk_id`). Identity
  is carried by the chunk's *position* (the ordinal of its body
  paragraph inside the document, plus the subchunk index inside
  that paragraph) together with the hash of its exact text.
  ``revision_id`` and absolute character offsets are deliberately
  NOT part of a chunk's identity, so editing one paragraph changes
  only that paragraph's chunk IDs: later paragraphs keep theirs
  even though their offsets move. Identical texts in different
  paragraphs never collide, because their ordinals differ.

``record_id`` and ``case_id`` are deliberately NOT computed here:
``record_id`` is the HTML daily record subrecord's existing stable
id, and ``case_id`` is the classroom case's stable identity (for
example ``L19-C01-work-transfer``). They are two separate identity
systems, carried in from the source data, and are never derived
from each other or from dates/content.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath

_SEPARATOR = "|"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def hash_text(text: str) -> str:
    """SHA-256 hex digest of ``text`` encoded as UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_component(value: str, name: str) -> str:
    if not value or value != value.strip() or _SEPARATOR in value:
        raise ValueError(
            f"{name} must be a non-empty token without surrounding "
            f"whitespace or {_SEPARATOR!r}, got {value!r}"
        )
    return value


def _require_composed_id(value: str, name: str) -> str:
    """Validate an already-composed ID (it legitimately contains ``|``)."""
    if not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty composed id, got {value!r}")
    return value


def _require_sha256(value: str, name: str) -> str:
    if not _SHA256_PATTERN.match(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest, got {value!r}")
    return value


def _normalize_path(path: str) -> str:
    """Normalize a repository-relative POSIX path for an ID."""
    if "\\" in path:
        raise ValueError(f"path must use POSIX separators, got {path!r}")
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ValueError(
            f"path must be a non-empty relative path inside the repository, got {path!r}"
        )
    return str(pure)


def make_document_id(source_type: str, repository: str, path: str) -> str:
    """Compose the stable ``document_id`` for one source file."""
    return _SEPARATOR.join(
        (
            _require_component(source_type, "source_type"),
            _require_component(repository, "repository"),
            _normalize_path(path),
        )
    )


def make_revision_id(document_id: str, content_hash: str) -> str:
    """Compose the ``revision_id`` for one version of a document."""
    return _SEPARATOR.join(
        (
            _require_composed_id(document_id, "document_id"),
            _require_sha256(content_hash, "content_hash"),
        )
    )


def _require_index(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


def make_chunk_id(
    document_id: str,
    chunker_version: str,
    paragraph_ordinal: int,
    subchunk_index: int,
    chunk_text_hash: str,
) -> str:
    """Compose the ``chunk_id`` for one chunk of one document.

    The composition is ``document_id | chunker_version |
    paragraph_ordinal | subchunk_index | chunk_text_hash`` where
    ``paragraph_ordinal`` is the 0-based ordinal of the chunk's body
    paragraph within the document, ``subchunk_index`` is the 0-based
    index of the chunk inside that paragraph (0 unless the paragraph
    was split for length), and ``chunk_text_hash`` is the SHA-256 of
    the chunk's exact text.

    Stability contract (M4a):

    * Editing one paragraph changes only that paragraph's chunk
      IDs — its text hash changes; other paragraphs keep their
      ordinal, subchunk index and hash, so their IDs are unchanged
      even when their absolute offsets shift.
    * ``revision_id`` is not an input: a new document revision does
      not by itself re-identify unchanged chunks.
    * Heading-path changes do not propagate into chunk IDs.
    * Identical texts at different positions get different IDs via
      ``paragraph_ordinal``; identical subchunks of one paragraph
      (possible after a hard character split) via ``subchunk_index``.

    Known boundary: inserting or deleting a paragraph *before* a
    paragraph renumbers the later paragraphs' ordinals and therefore
    changes their chunk IDs. That is inherent to any position-based
    identity; content-based occurrence counting was rejected because
    editing a paragraph into a duplicate of another one would have
    renumbered the *other* paragraph's chunks. A ``chunker_version``
    change creates a new ID space for the whole document by design.
    """
    return _SEPARATOR.join(
        (
            _require_composed_id(document_id, "document_id"),
            _require_component(chunker_version, "chunker_version"),
            str(_require_index(paragraph_ordinal, "paragraph_ordinal")),
            str(_require_index(subchunk_index, "subchunk_index")),
            _require_sha256(chunk_text_hash, "chunk_text_hash"),
        )
    )
