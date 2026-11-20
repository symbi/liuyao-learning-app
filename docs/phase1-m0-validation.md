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

## Measured Instance Details

- **Tier:** AuraDB Free
- **Region:** GCP Singapore (`asia-southeast1`)
- **Console platform version:** `2026.10`
- **Database kernel:** `5.27-aura`
- **Edition:** `enterprise` as returned by `CALL dbms.components()`
- **Cypher:** 5 and 25 support was observed

The Console `2026.10` value identifies the Aura platform release shown by
Console. It differs from the database kernel version `5.27-aura` returned
by `CALL dbms.components()`. The kernel and actual observed behavior are the
source of truth for Cypher and driver behavior.

## Instance-Specific Results

The following were observed on the M0 Free instance and must not be presented
as universal limits or behavior for every AuraDB instance:

- `AuraDB Free` was reported with 200,000 nodes, 400,000 relationships, and
  1 GB storage. It was a single-node shared DBMS with no HA/SLA in the M0
  report; Phase 2 or other environments require fresh acceptance testing.
- The M0 instance had no SRV records and required a custom resolver.
- Direct `bolt://` was intermittent; routing with `neo4j://` plus the custom
  resolver was stable in M0.
- The macOS/Python CA trust environment required certifi for the observed
  certificate chain. TLS verification remained enabled; `TrustAll` was not
  used.
- Vector index creation, `ONLINE` status, query, and deletion passed.
- Real index tests passed at dimensions 128, 256, 384, 768, 1024, 1536, and
  3072. The M0 result only proves the highest tested dimension was 3072;
  it does not prove 3072 is the platform maximum. The official documented
  upper limit is 4096.
- `db.index.vector.queryNodes()` passed.
- `SEARCH n IN (VECTOR INDEX idx FOR $vec LIMIT 2) SCORE AS score` and direct
  `$vec` parameter passing passed on this instance, despite the kernel-report
  limitation noted by the original report.
