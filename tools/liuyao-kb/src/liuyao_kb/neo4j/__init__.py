"""Neo4j access for liuyao-kb.

All AuraDB-specific connection behaviour lives in
:mod:`liuyao_kb.neo4j.driver`. Other modules must not open drivers
themselves.
"""

from liuyao_kb.neo4j.driver import (
    ConnectionProfile,
    build_ca,
    build_driver,
    build_profile,
    build_session,
    check_connection,
    classify_connection_error,
)

__all__ = [
    "ConnectionProfile",
    "build_ca",
    "build_driver",
    "build_profile",
    "build_session",
    "check_connection",
    "classify_connection_error",
]
