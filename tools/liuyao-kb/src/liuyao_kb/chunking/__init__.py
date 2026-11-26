"""Deterministic chunking of parsed sources (Phase 1 M4a)."""

from liuyao_kb.chunking.chunker import (
    CHUNKER_VERSION,
    MAX_CHUNK_CHARS,
    Chunk,
    ChunkingResult,
    ChunkingStats,
    chunk_document,
    chunk_sections,
)

__all__ = [
    "CHUNKER_VERSION",
    "MAX_CHUNK_CHARS",
    "Chunk",
    "ChunkingResult",
    "ChunkingStats",
    "chunk_document",
    "chunk_sections",
]
