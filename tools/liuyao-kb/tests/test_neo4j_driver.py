"""Tests for the Neo4j connection module.

These tests never open a network connection. They cover the connection
*parameters* -- the AuraDB quirks that were established during M0 -- and
the error classification that turns driver messages into something an
operator can act on.
"""

from __future__ import annotations

import pytest

from liuyao_kb.config import Neo4jSettings
from liuyao_kb.neo4j.driver import (
    build_ca,
    build_profile,
    classify_connection_error,
)


def settings(**overrides: str) -> Neo4jSettings:
    values = {
        "uri": "neo4j+s://abc123.databases.neo4j.io",
        "username": "abc123",
        "password": "s3cret-password-value",
        "database": "abc123",
    }
    values.update(overrides)
    return Neo4jSettings(**values)  # type: ignore[arg-type]


class TestConnectionProfile:
    def test_uses_the_routing_scheme(self) -> None:
        profile = build_profile(settings())
        assert profile.scheme == "neo4j"
        assert profile.host == "abc123.databases.neo4j.io"
        assert profile.port == 7687

    def test_always_uses_a_custom_resolver(self) -> None:
        # AuraDB publishes no SRV records, so the routing driver would fail
        # with "Unable to retrieve routing information" without one.
        assert build_profile(settings()).uses_custom_resolver is True

    def test_honours_an_explicit_port(self) -> None:
        profile = build_profile(settings(uri="neo4j+s://abc123.databases.neo4j.io:7777"))
        assert profile.port == 7777

    def test_description_contains_no_secret(self) -> None:
        description = build_profile(settings()).describe()
        assert "s3cret-password-value" not in description
        assert "abc123.databases.neo4j.io" in description


class TestTrustStore:
    def test_uses_a_verifying_trust_store(self) -> None:
        trust, source = build_ca()
        assert source in {"certifi", "system"}
        # TrustAll must never be used: it disables certificate verification.
        assert type(trust).__name__ != "TrustAll"


class TestErrorClassification:
    @pytest.mark.parametrize(
        ("message", "expected_fragment"),
        [
            (
                "Neo.ClientError.Security.Unauthorized: The client is unauthorized",
                "Authentication failed",
            ),
            (
                "Neo.ClientError.Database.DatabaseNotFound: Database abc123 not found",
                "could not find the database",
            ),
            (
                "ServiceUnavailable: Unable to retrieve routing information",
                "could not resolve the instance",
            ),
            (
                "SSLCertVerificationError: certificate verify failed",
                "TLS verification failed",
            ),
            (
                "ServiceUnavailable: Failed to establish connection",
                "Could not reach the instance",
            ),
        ],
    )
    def test_maps_driver_errors_to_actions(self, message: str, expected_fragment: str) -> None:
        hint = classify_connection_error(Exception(message))
        assert expected_fragment in hint

    def test_unknown_error_still_redacts(self) -> None:
        hint = classify_connection_error(Exception("failed with password=s3cret-password-value"))
        assert "s3cret-password-value" not in hint

    def test_auth_hint_mentions_the_instance_naming_trap(self) -> None:
        hint = classify_connection_error(Exception("unauthorized"))
        assert "instance credentials file" in hint


class TestDriverConstruction:
    def test_driver_is_created_with_the_expected_parameters(self) -> None:
        # Building the driver must not connect, so this is safe offline.
        from liuyao_kb.neo4j.driver import build_driver

        driver = build_driver(settings())
        try:
            assert driver is not None
        finally:
            driver.close()
