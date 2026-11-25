# liuyao-kb container image — the Cloud Run Jobs runtime for Phase 1
# batch work (M3 schema job first; M4/M5 jobs reuse the same image).
#
# Build context: this directory (tools/liuyao-kb).
#   docker build -t liuyao-kb:dev tools/liuyao-kb
#
# The image contains code only. Neo4j credentials are NEVER baked in:
# at runtime the Cloud Run Job mounts the Secret Manager secret
# `neo4j-aura-credentials` as /secrets/m0.env and sets
# LIUYAO_KB_CONFIG_DIR=/secrets, and the existing load_config() reads
# it from there. See deploy/README.md.
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
# Read-only default: running the image with no arguments only checks
# the schema. The schema Job passes explicit arguments (schema init)
# when a write is intended and authorized.
ENTRYPOINT ["liuyao-kb"]
CMD ["schema", "check"]
