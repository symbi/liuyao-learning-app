# liuyao-kb

Phase 1 knowledge-base tooling for the Liuyao learning project: a local
incremental importer and a query tool that produce an evidence pack for
ChatGPT to analyse.

Runs on the user's Mac. Talks to a single Neo4j AuraDB Free database.
No Docker, no server to deploy, no second database.

## Status

M1 — project skeleton. The commands exist and are tested; ingestion,
embedding and querying arrive in later milestones.

| Command | M1 behaviour |
|---|---|
| `liuyao-kb doctor` | Checks configuration, credentials and database access. Runs with no credentials. |
| `liuyao-kb sources list` | Lists the allowlisted sources and whether each is enabled. |
| `liuyao-kb ingest run --dry-run` | Reports what would be imported. Writes nothing. |

## Setup

```bash
cd tools/liuyao-kb
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
cp .env.example .env          # then fill in the values
cp sources.example.yaml sources.yaml
```

Both `.env` and `sources.yaml` are gitignored. Only the `.example`
templates are committed.

### Credentials

`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` and `NEO4J_DATABASE`
come from the Aura Console instance credentials file. Nothing is
hardcoded, and nothing is printed: the password never appears in logs,
`doctor` output, or any generated file.

The loader reads `~/.config/liuyao-kb/m0.env` first, then a local `.env`.
A variable already set in the environment is never replaced by a file,
and the warning that records the override names the variable only.

AuraDB names the instance **user** and **user database** after the
instance id, and that id is *not* always `neo4j`. Read both values from
the credentials file rather than assuming.

## Connecting to AuraDB

All AuraDB-specific connection logic lives in
`src/liuyao_kb/neo4j/driver.py`. The importer, schema writer and query
tool all go through it, so the quirks below are fixed in one place.

The standard Aura URI is `neo4j+s://<id>.databases.neo4j.io`. The driver
does **not** use it verbatim, because three things break on AuraDB:

1. **No SRV records.** The routing driver resolves the host through a
   DNS SRV lookup; with no SRV record it fails with "Unable to retrieve
   routing information". A custom resolver returns the instance host
   directly.
2. **Direct `bolt://` is unreliable.** It intermittently fails with
   "Database not found", because a request can land on a cluster member
   that has not yet registered the user database. The routing scheme
   resolves the real member first.
3. **The certificate chain does not verify against the system trust
   store.** It is rooted at an SSL.com root that the macOS Keychain has
   but `/private/etc/ssl/cert.pem` does not, so Python's default context
   rejects it with "self-signed certificate in certificate chain". The
   `certifi` bundle carries that root.

The resulting configuration is:

```python
GraphDatabase.driver(
    f"neo4j://{host}:{port}",
    auth=neo4j.basic_auth(username, password),
    encrypted=True,
    trusted_certificates=neo4j.TrustCustomCAs(certifi.where()),
    resolver=lambda addr: [(host, port)],
)
```

Certificate verification stays on. `TrustAll` is never used.

Both the standard `neo4j+s://` form and this verified form are recorded in
[docs/phase1-m0-validation.md](../../../docs/phase1-m0-validation.md).

## Source policy

The importer reads an explicit allowlist only. It never scans the home
directory.

| Source | Default | Notes |
|---|---|---|
| `curated_lesson_note` | on | The primary chunk and embedding source. |
| `classroom_case` | on | Deterministic mapping; no LLM re-derivation. |
| `raw_asr` | **off** | ~70% accurate transcripts. Metadata only unless explicitly enabled. |
| `daily_casting` | **off** | Personal material. |
| `pdf_reference` | **off** | Only files the user has reviewed. |
| `external_project_doc` | **off** | Empty until repository, paths and licence are confirmed. |

Raw ASR and curated notes are separate tracks. A transcript never enters
the main chunk, embedding or rule-extraction pipeline by accident.

## Development

```bash
.venv/bin/python -m pytest          # tests
.venv/bin/python -m ruff check .    # lint
.venv/bin/python -m ruff format .   # format
.venv/bin/python -m mypy            # types
```

## Layout

```text
tools/liuyao-kb/
├── pyproject.toml
├── .env.example
├── sources.example.yaml
├── src/liuyao_kb/
│   ├── cli.py              # doctor / sources list / ingest dry-run
│   ├── config.py           # credential loading, redaction
│   ├── logging_setup.py    # logging with a redaction filter
│   ├── neo4j/driver.py     # the only place that opens a Neo4j connection
│   └── sources/config.py   # the source allowlist
└── tests/
```

## Related documents

- [Phase 1 implementation plan](../../../docs/phase1-implementation-plan.md)
- [Phase 1 operating model](../../../docs/phase1-operating-model.md)
- [M0 validation results](../../../docs/phase1-m0-validation.md)
- [Phase 1 progress](../../../docs/phase1-progress.md)
