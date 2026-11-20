"""Configuration loading for liuyao-kb.

All credentials come from the environment (optionally seeded from a local
``.env`` file). Nothing in this module hardcodes a connection string, a
user name, a password, or a database name.

Two rules matter more than the rest:

* Secrets are never rendered. ``Config`` never exposes the password through
  ``repr``/``str``, and every log helper runs values through
  :func:`redact` first.
* A missing credential is a normal, reportable state -- not an exception.
  ``liuyao-kb doctor`` must be able to run and explain what is missing
  without any database access.
"""

from __future__ import annotations

import os
import re
from dataclasses import field
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

#: Default directory for local, untracked configuration and state.
DEFAULT_CONFIG_DIR: Final[Path] = Path.home() / ".config" / "liuyao-kb"

#: Names that must never appear in logs or reports.
_SECRET_KEY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?P<key>password|passwd|pwd|secret|token|api[_-]?key|x[_-]?api[_-]?key|"
    r"client[_-]?secret|credential)"
    r"\b\s*(?P<sep>[:=])\s*"
    r"(?P<value>=*(?:\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|[^\s,;\]\"']+))",
    re.IGNORECASE,
)

_AUTHORIZATION_BEARER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?P<prefix>authorization\s*:\s*bearer\s+)[^\s,;'\"]+",
    re.IGNORECASE,
)

#: Credentials embedded in a URI (``neo4j+s://user:pass@host``).
_URI_USERINFO_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?P<scheme>(?:neo4j|neo4j\+s|bolt|bolt\+s)://)[^/\s@]+@",
    re.IGNORECASE,
)


def redact(text: str) -> str:
    """Remove anything that looks like a secret from ``text``."""
    text = _URI_USERINFO_PATTERN.sub(r"\1<redacted>@", text)
    text = _AUTHORIZATION_BEARER_PATTERN.sub(r"\g<prefix><redacted>", text)
    return _SECRET_KEY_PATTERN.sub(_mask_secret_value, text)


def _mask_secret_value(match: re.Match[str]) -> str:
    """Replace the complete secret value and preserve key/normal separator."""
    key = match.group("key")
    separator = match.group("sep")
    return f"{key}{separator}<redacted>"


def redact_uri(uri: str) -> str:
    """Return a URI safe to print: scheme and host only.

    The host is not a secret -- it is needed to identify which instance is
    being talked about -- but user info, path, query and fragment are not
    printed.
    """
    from urllib.parse import urlsplit

    try:
        parts = urlsplit(uri)
    except ValueError:
        return "<unparseable-uri>"
    if not parts.scheme:
        return "<unparseable-uri>"
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return f"{parts.scheme}://{host}"


def instance_id_from_uri(uri: str) -> str | None:
    """Extract the host's leading instance identifier when present.

    This helper is useful for host identification only. It must not be used
    as the basis for assuming an AuraDB username or user-database name:
    always read those values from the instance Credentials file or external
    configuration.
    """
    from urllib.parse import urlsplit

    try:
        host = urlsplit(uri).hostname or ""
    except ValueError:
        return None
    if not host:
        return None
    head = host.split(".")[0]
    return head or None


class Neo4jSettings(BaseModel):
    """Connection settings for one Neo4j database."""

    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)

    uri: str = Field(..., description="Aura connection URI, e.g. neo4j+s://...")
    username: str = Field(..., description="Instance user name")
    password: SecretStr = Field(..., description="Instance password")
    database: str = Field(..., description="User database name")

    @field_validator("uri")
    @classmethod
    def _validate_uri(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Neo4j URI must not be empty")

        from urllib.parse import urlsplit

        try:
            parts = urlsplit(value)
        except ValueError:
            raise ValueError("Neo4j URI is malformed") from None

        accepted_schemes = ("neo4j", "neo4j+s", "bolt", "bolt+s")
        if parts.scheme.lower() not in accepted_schemes:
            raise ValueError(
                "Neo4j URI must use neo4j://, neo4j+s://, bolt:// or bolt+s:// "
                f"(got scheme {parts.scheme or '<missing>'})"
            )
        if parts.username is not None or parts.password is not None:
            raise ValueError(
                "Neo4j URI must not contain username/password userinfo; "
                "pass authentication through NEO4J_USERNAME and NEO4J_PASSWORD"
            )
        if not parts.hostname:
            raise ValueError("Neo4j URI must include a host")
        return value

    @property
    def safe_uri(self) -> str:
        """URI safe to print."""
        return redact_uri(self.uri)

    @property
    def instance_id(self) -> str | None:
        """Aura instance id derived from the URI host, if present."""
        return instance_id_from_uri(self.uri)


class GeminiSettings(BaseModel):
    """Google Gemini settings.

    Only the embedding/generation *model ids* live here. The API key is
    stored separately as a secret.
    """

    model_config = ConfigDict(frozen=True)

    api_key: SecretStr = Field(default=SecretStr(""))
    generation_model: str = Field(default="gemini-2.5-flash")
    embedding_model: str = Field(default="gemini-embedding-2")
    embedding_dimensions: int = Field(default=1536, ge=1, le=4096)


class Config(BaseModel):
    """Runtime configuration for the whole tool."""

    model_config = ConfigDict(frozen=True)

    neo4j: Neo4jSettings | None = None
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    config_dir: Path = Field(default=DEFAULT_CONFIG_DIR)
    log_level: str = Field(default="INFO")
    #: Extra local source allowlist, resolved by M2+.
    sources_path: Path | None = None
    #: Warnings collected while loading, shown by ``doctor``.
    warnings: list[str] = field(default_factory=list)

    @property
    def has_neo4j(self) -> bool:
        return self.neo4j is not None

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini.api_key.get_secret_value())


def _read_env_file(path: Path) -> dict[str, str]:
    """Parse a ``KEY=VALUE`` file. Comments and blank lines are ignored."""
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _candidate_env_files(config_dir: Path) -> list[Path]:
    """Where a local env file may live, highest priority first.

    ``m0.env`` is the credential file kept outside the repository, under
    the config directory (by default ``~/.config/liuyao-kb/m0.env``).
    """
    return [
        config_dir / "m0.env",
        config_dir / ".env",
        Path.cwd() / ".env",
        Path.cwd() / "tools" / "liuyao-kb" / ".env",
    ]


def _apply_env_file(environment: dict[str, str], path: Path, warnings: list[str]) -> None:
    """Fill missing keys from ``path``. Keys already set are left alone.

    The mapping in ``environment`` is the process environment, or the
    explicit mapping tests pass in its place. Either one wins over a file.
    The warning names the keys and the file, never the values.
    """
    file_values = _read_env_file(path)
    if not file_values:
        return
    kept: list[str] = []
    for key, value in file_values.items():
        current = environment.get(key)
        if current is None:
            environment[key] = value
        elif current != value:
            kept.append(key)
    if kept:
        warnings.append(
            "Already-set variables were not replaced by " + path.name + ": " + ", ".join(kept)
        )


def load_config(
    env: dict[str, str] | None = None,
    *,
    config_dir: Path | None = None,
    dotenv: bool = True,
) -> Config:
    """Build a :class:`Config` from the environment.

    ``env`` overrides the process environment, which is what the tests use.
    Credentials are never required: a missing Neo4j password yields a
    config with ``neo4j=None`` plus a warning, so ``doctor`` can explain
    the situation instead of crashing.
    """
    environment: dict[str, str] = dict(os.environ if env is None else env)
    warnings: list[str] = []

    resolved_dir = config_dir or Path(environment.get("LIUYAO_KB_CONFIG_DIR") or DEFAULT_CONFIG_DIR)
    resolved_dir = Path(resolved_dir).expanduser()

    if dotenv:
        for candidate in _candidate_env_files(resolved_dir):
            if not candidate.is_file():
                continue
            # A real environment variable always wins over a file value.
            _apply_env_file(environment, candidate, warnings)

    neo4j = _build_neo4j_settings(environment, warnings)
    gemini = _build_gemini_settings(environment, warnings)

    sources_path = environment.get("LIUYAO_KB_SOURCES")
    return Config(
        neo4j=neo4j,
        gemini=gemini,
        config_dir=resolved_dir,
        log_level=environment.get("LIUYAO_KB_LOG_LEVEL", "INFO").upper(),
        sources_path=Path(sources_path).expanduser() if sources_path else None,
        warnings=warnings,
    )


def _build_neo4j_settings(environment: dict[str, str], warnings: list[str]) -> Neo4jSettings | None:
    """Assemble Neo4j settings, or explain what is missing."""
    uri = environment.get("NEO4J_URI", "").strip()
    username = environment.get("NEO4J_USERNAME", "").strip()
    password = environment.get("NEO4J_PASSWORD", "").strip()
    database = environment.get("NEO4J_DATABASE", "").strip()

    missing = [
        name
        for name, value in (
            ("NEO4J_URI", uri),
            ("NEO4J_USERNAME", username),
            ("NEO4J_PASSWORD", password),
            ("NEO4J_DATABASE", database),
        )
        if not value
    ]
    if missing:
        if len(missing) == 4:
            # Nothing configured at all -- normal for a fresh checkout.
            return None
        warnings.append("Neo4j settings incomplete, missing: " + ", ".join(missing))
        return None

    try:
        return Neo4jSettings(
            uri=uri,
            username=username,
            password=SecretStr(password),
            database=database,
        )
    except Exception as exc:  # pydantic validation error
        warnings.append(f"Neo4j settings invalid: {redact(str(exc))}")
        return None


def _build_gemini_settings(environment: dict[str, str], warnings: list[str]) -> GeminiSettings:
    """Assemble Gemini settings."""
    try:
        dimensions = int(environment.get("GEMINI_EMBEDDING_DIMENSIONS", "1536"))
    except ValueError:
        warnings.append("GEMINI_EMBEDDING_DIMENSIONS is not a number, using 1536")
        dimensions = 1536

    return GeminiSettings(
        api_key=SecretStr(environment.get("GEMINI_API_KEY", "").strip()),
        generation_model=environment.get("GEMINI_GENERATION_MODEL", "gemini-2.5-flash").strip(),
        embedding_model=environment.get("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2").strip(),
        embedding_dimensions=dimensions,
    )
