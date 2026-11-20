# Phase 1 M0 — AuraDB Free Validation

## Acceptance Summary

- Platform: Neo4j AuraDB Free
- Neo4j: 5.27-aura
- Python: 3.12.13
- Neo4j Python Driver: 6.4.1
- Vector Index: creation, ONLINE status, query, and deletion passed
- Dimensions verified: 128, 256, 384, 768, 1024, 1536, 3072
- Cypher SEARCH syntax: verified
- Direct `$vec` parameter: verified

## Connection Requirements

The working AuraDB setup must account for:

- Aura-provided username and user database names (instance-specific; not assumed to be `neo4j`)
- Custom resolver for the instance host
- Verified TLS using the certifi CA bundle when required by the macOS/Python trust environment

This M0 result is frozen for Phase 1 and must not be redesigned or re-run as part of M1.

## Credential Handling

The original M0 report is stored outside this repository at `/tmp/liuyao-m0/M0-REPORT.md`. Secrets remain outside the repository under `~/.config/liuyao-kb/m0.env` and must never be copied into Git or documentation.
