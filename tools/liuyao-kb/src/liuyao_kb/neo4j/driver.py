"""Neo4j connection handling for liuyao-kb.

This is the **only** module that knows how to connect to AuraDB. The
importer, the query tool and the schema writer all go through
:func:`build_driver`, so AuraDB's quirks are fixed in one place.

Why the connection is not just ``neo4j+s://<host>``:

The following are measured behavior of the current M0 GCP Singapore AuraDB
Free instance. They are not asserted as universal behavior for every AuraDB
instance:

* **The M0 instance exposed no SRV record.** The routing driver resolves the
  host through DNS SRV lookup before it can connect, and with no SRV
  record the driver fails with "Unable to retrieve routing information".
  A custom resolver that returns the instance host directly removes that
  dependency.
* **On the M0 instance, direct ``bolt://`` was unreliable.** It intermittently
  failed with "Database not found" because the request could land on a cluster
  member that had not yet registered the user database. The routing scheme
  resolved the real member first.
* **On the M0 instance, the certificate chain did not verify against the
  system trust store.** The chain was rooted at an SSL.com root that the macOS
  Keychain has but ``/private/etc/ssl/cert.pem`` does not, so Python's default
  context rejected it. The ``certifi`` bundle carried that root.

Certificate verification stays on. ``TrustAll`` is never used: it would
make every connection an unauthenticated man-in-the-middle waiting to
happen.

The instance user name and database name are **not** derived here. They
come from configuration, because AuraDB names them per instance and they
are not universally ``neo4j``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import neo4j

from liuyao_kb.config import Neo4jSettings, redact

logger = logging.getLogger(__name__)

#: Default Bolt port for AuraDB instances.
DEFAULT_BOLT_PORT = 7687


@dataclass(frozen=True)
class ConnectionProfile:
    """How the driver is actually going to connect.

    Kept separate from :class:`Neo4jSettings` because the settings are
    what the user configured, while this is what the driver needs.
    Only sanitized, non-secret connection details are stored here.
    """

    safe_uri: str
    database: str
    scheme: str
    host: str
    port: int
    uses_custom_resolver: bool
    ca_source: str

    def describe(self) -> str:
        """Human-readable, secret-free summary for ``doctor``."""
        return (
            f"{self.scheme}://{self.host}:{self.port} "
            f"(database={self.database}, "
            f"resolver={'custom' if self.uses_custom_resolver else 'dns'}, "
            f"ca={self.ca_source})"
        )


def _split_host_port(uri: str) -> tuple[str, int]:
    """Extract host and port from a connection URI."""
    from urllib.parse import urlsplit

    parts = urlsplit(uri)
    host = parts.hostname or ""
    port = parts.port or DEFAULT_BOLT_PORT
    if not host:
        raise ValueError("Connection URI has no host")
    return host, port


def _build_resolver(host: str, port: int) -> Callable[[neo4j.Address], list[neo4j.Address]]:
    """A resolver that returns the instance host without an SRV lookup.

    The driver calls ``resolver(address)`` and expects an iterable of
    ``Address`` instances.
    """

    def resolve(address: neo4j.Address) -> list[neo4j.Address]:
        return [neo4j.Address((host, port))]

    return resolve


def build_ca() -> tuple[Any, str]:
    """Return the trust store and a label describing where it came from.

    Prefers the ``certifi`` bundle, which carries the SSL.com root that
    AuraDB's certificate chain is rooted in. Falls back to the system
    trust store.
    """
    try:
        import certifi

        return neo4j.TrustCustomCAs(certifi.where()), "certifi"
    except ImportError:
        logger.warning("certifi is not installed; falling back to the system trust store")
        return neo4j.TrustSystemCAs(), "system"


def build_profile(settings: Neo4jSettings) -> ConnectionProfile:
    """Work out the concrete connection parameters for ``settings``."""
    host, port = _split_host_port(settings.uri)
    _, ca_source = build_ca()
    return ConnectionProfile(
        safe_uri=settings.safe_uri,
        database=settings.database,
        scheme="neo4j",
        host=host,
        port=port,
        uses_custom_resolver=True,
        ca_source=ca_source,
    )


def build_driver(settings: Neo4jSettings) -> neo4j.Driver:
    """Create a Neo4j driver configured for AuraDB.

    The driver is lazy: no connection is opened until the first query.
    """
    profile = build_profile(settings)
    ca, _ = build_ca()

    logger.info(
        "Creating Neo4j driver for %s as user %r on database %r",
        profile.describe(),
        settings.username,
        profile.database,
    )

    return neo4j.GraphDatabase.driver(
        f"{profile.scheme}://{profile.host}:{profile.port}",
        auth=neo4j.basic_auth(settings.username, settings.password.get_secret_value()),
        encrypted=True,
        trusted_certificates=ca,
        resolver=_build_resolver(profile.host, profile.port),
    )


@contextmanager
def build_session(
    settings: Neo4jSettings, driver: neo4j.Driver | None = None
) -> Iterator[neo4j.Session]:
    """Open a session against the configured database.

    ``driver`` may be supplied to reuse an existing driver; otherwise a
    short-lived one is created and closed with the session.
    """
    if driver is None:
        driver = build_driver(settings)
        try:
            with driver.session(database=settings.database) as session:
                yield session
        finally:
            driver.close()
    else:
        with driver.session(database=settings.database) as session:
            yield session


def classify_connection_error(exc: Exception) -> str:
    """Turn a driver exception into an actionable message.

    The bare driver errors for AuraDB are actively misleading -- an
    authentication failure and a missing database both surface as a
    generic "Database not found". This maps the common cases to what the
    operator should actually check.
    """
    text = str(exc)
    lowered = text.lower()

    if "unauthorized" in lowered or "invalid credential" in lowered:
        return (
            "Authentication failed. Check NEO4J_USERNAME and NEO4J_PASSWORD against the "
            "instance credentials file from Aura Console. Note that AuraDB names the "
            "instance user after the instance id, not always 'neo4j'."
        )
    if "databasenotfound" in lowered or "database not found" in lowered:
        return (
            "The server could not find the database. Check NEO4J_DATABASE against the "
            "instance credentials file from Aura Console. AuraDB names the user database "
            "after the instance id, not always 'neo4j'."
        )
    if "unable to retrieve routing information" in lowered:
        return (
            "The driver could not resolve the instance. This usually means the SRV lookup "
            "failed; liuyao-kb supplies a custom resolver, so check that the URI host is "
            "correct."
        )
    if "certificate" in lowered or "ssl" in lowered:
        return (
            "TLS verification failed. The instance certificate chain may not be trusted by "
            "the current CA bundle; install 'certifi' and retry."
        )
    if "connection refused" in lowered or "failed to establish" in lowered:
        return (
            "Could not reach the instance. Check network connectivity and that the "
            "instance is RUNNING in Aura Console."
        )
    return f"Unclassified Neo4j error: {redact(text)}"


def check_connection(settings: Neo4jSettings) -> dict[str, Any]:
    """Run a connectivity check and return a structured result.

    Used by ``liuyao-kb doctor``. Never raises: failures are returned as
    data so the CLI can report every problem it found in one pass.
    """
    result: dict[str, Any] = {
        "ok": False,
        "target": settings.safe_uri,
        "username": settings.username,
        "database": settings.database,
        "profile": "",
        "server_version": None,
        "edition": None,
        "error": None,
        "hint": None,
    }

    try:
        profile = build_profile(settings)
        result["profile"] = profile.describe()
    except Exception as exc:
        result["error"] = redact(str(exc))
        result["hint"] = "Check that NEO4J_URI is a valid Aura connection URI."
        return result

    driver = None
    try:
        driver = build_driver(settings)
        driver.verify_connectivity()
        with driver.session(database=settings.database) as session:
            row = session.run(
                "CALL dbms.components() YIELD name, versions, edition RETURN versions, edition"
            ).single()
        if row is not None:
            result["server_version"] = row["versions"][0]
            result["edition"] = row["edition"]
        result["ok"] = True
    except Exception as exc:
        result["error"] = redact(f"{type(exc).__name__}: {exc}")
        result["hint"] = classify_connection_error(exc)
    finally:
        if driver is not None:
            driver.close()
    return result
