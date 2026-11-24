# liuyao-kb

Phase 1 knowledge-base tooling for the Liuyao learning project: an
incremental importer and retrieval tooling for a Neo4j knowledge base.
From M7, a Cloud Run analysis service turns retrieval results into the
sourced report shown in the HTML app.

Production execution runs in the cloud (Google Cloud Run: Jobs for imports and batch work, a Service for the online analysis API); local runs are for development only. Talks to a single Neo4j AuraDB Free database.
One graph database, one cloud runtime (Cloud Run).

## Status

M1 and M2 are complete (project skeleton, source adapters, classroom-case mapping). Schema management (M3), cloud ingestion (M4), embedding (M5) and the online analysis API (M7) arrive in later milestones; none of them has started yet. The commands below exist and are tested; ingestion,
embedding and querying arrive in later milestones.

| Command | Behaviour |
|---|---|
| `liuyao-kb doctor` | Checks configuration, credentials and database access. Runs with no credentials. |
| `liuyao-kb sources list` | Lists the allowlisted sources and whether each is enabled. |
| `liuyao-kb ingest run --dry-run` | Reports what would be imported. Writes nothing. |

## Setup

```bash
cd tools/liuyao-kb
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"

mkdir -p ~/.config/liuyao-kb
chmod 700 ~/.config/liuyao-kb
if [ ! -f ~/.config/liuyao-kb/m0.env ]; then
  cp .env.example ~/.config/liuyao-kb/m0.env
fi
chmod 600 ~/.config/liuyao-kb/m0.env

cp sources.example.yaml sources.yaml
```

Fill in real credentials only in `~/.config/liuyao-kb/m0.env` on the
local machine (development only). Production credentials live in Google Secret Manager and are bound to Cloud Run at runtime; they are never stored in this repository. Do not ask a coding agent to read or print that file.

Both `sources.yaml` and local env files are gitignored. Only `.example`
templates are committed.

### Credentials

`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` and `NEO4J_DATABASE`
come from the Aura Console instance credentials file. Nothing is
hardcoded, and nothing is printed: the password never appears in logs,
`doctor` output, or any generated file.

The loader reads `~/.config/liuyao-kb/m0.env` first, then optional local
`.env` files. A variable already set in the OS environment always wins.
Warnings name only conflicting variable names, never values.

URI authentication is not embedded in `NEO4J_URI`. Keep the URI host-only
and provide `NEO4J_USERNAME` and `NEO4J_PASSWORD` separately. The tool
rejects URI userinfo and redacts URI representations.

For the current M0 Singapore Free instance, the observed **instance user**
and **user database** were both the instance ID rather than `neo4j`. This is
an M0 result, not a rule for every AuraDB instance. For every other instance,
read both values from the downloaded Aura Credentials file and never derive
or assume them from the URI instance ID.

## Connecting to AuraDB

All AuraDB-specific connection logic lives in
`src/liuyao_kb/neo4j/driver.py`. The importer, schema writer and query
tool all go through it, so the quirks below are fixed in one place.

The standard Aura URI is `neo4j+s://<id>.databases.neo4j.io`. In the
specific M0 Singapore Free instance, the driver **did not** use it
verbatim because these measured behaviors required workarounds. They are
not asserted as universal behavior for every AuraDB deployment:

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
[docs/phase1-m0-validation.md](../../docs/phase1-m0-validation.md).

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

- [Phase 1 implementation plan](../../docs/phase1-implementation-plan.md)
- [Phase 1 operating model](../../docs/phase1-operating-model.md)
- [M0 validation results](../../docs/phase1-m0-validation.md)
- [Phase 1 progress](../../docs/phase1-progress.md)
