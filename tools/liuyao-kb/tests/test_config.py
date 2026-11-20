"""Tests for configuration loading and secret redaction."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from liuyao_kb.config import (
    Config,
    Neo4jSettings,
    instance_id_from_uri,
    load_config,
    redact,
    redact_uri,
)

FULL_ENV = {
    "NEO4J_URI": "neo4j+s://abc123.databases.neo4j.io",
    "NEO4J_USERNAME": "abc123",
    "NEO4J_PASSWORD": "s3cret-password-value",
    "NEO4J_DATABASE": "abc123",
}


class TestRedaction:
    def test_masks_key_value_pairs(self) -> None:
        assert "hunter2" not in redact("password=hunter2")
        assert "abc" not in redact("api_key=abc")
        assert "xyz" not in redact("token: xyz")

    def test_masks_password_colon_and_extra_equals_residue(self) -> None:
        text = redact("password: hunter2 password==second-secret")
        assert "hunter2" not in text
        assert "second-secret" not in text
        assert "password==" not in text

    def test_masks_bearer_authorization(self) -> None:
        text = redact("Authorization: Bearer fake-bearer-token")
        assert "fake-bearer-token" not in text
        assert "Authorization: Bearer <redacted>" in text

    def test_masks_multiple_secrets_and_keeps_normal_fields(self) -> None:
        text = redact(
            "password=first-secret token=fake-token api_key=fake-api-key "
            "log_level=DEBUG database=neo4j"
        )
        assert "first-secret" not in text
        assert "fake-token" not in text
        assert "fake-api-key" not in text
        assert "log_level=DEBUG" in text
        assert "database=neo4j" in text

    def test_masks_credentials_embedded_in_a_uri(self) -> None:
        text = "could not connect to neo4j+s://user:pass@host.databases.neo4j.io"
        redacted = redact(text)
        assert "pass@" not in redacted
        assert "user:" not in redacted
        assert "host.databases.neo4j.io" in redacted

    def test_redact_uri_keeps_scheme_and_host_only(self) -> None:
        result = redact_uri("neo4j+s://user:pass@abc123.databases.neo4j.io:7687/path")
        assert result == "neo4j+s://abc123.databases.neo4j.io:7687"
        assert "pass" not in result

    def test_redact_uri_handles_garbage(self) -> None:
        assert redact_uri("not a uri") == "<unparseable-uri>"

    def test_config_never_prints_the_password(self) -> None:
        settings = Neo4jSettings(
            uri="neo4j+s://abc123.databases.neo4j.io",
            username="abc123",
            password="s3cret-password-value",
            database="abc123",
        )
        rendered = repr(settings)
        assert "s3cret-password-value" not in rendered
        assert settings.password.get_secret_value() == "s3cret-password-value"


class TestInstanceId:
    @pytest.mark.parametrize(
        ("uri", "expected"),
        [
            ("neo4j+s://abc123.databases.neo4j.io", "abc123"),
            ("neo4j+s://abc123.databases.neo4j.io:7687", "abc123"),
            ("bolt+s://abc123.databases.neo4j.io", "abc123"),
            ("not a uri", None),
            ("", None),
        ],
    )
    def test_extracts_instance_id(self, uri: str, expected: str | None) -> None:
        assert instance_id_from_uri(uri) == expected


class TestLoadConfig:
    def test_missing_credentials_is_not_an_error(self) -> None:
        config = load_config(env={}, dotenv=False)
        assert config.neo4j is None
        assert config.has_neo4j is False

    def test_loads_full_neo4j_settings(self) -> None:
        config = load_config(env=dict(FULL_ENV), dotenv=False)
        assert config.neo4j is not None
        assert config.neo4j is not None
        assert config.neo4j.username == "abc123"
        assert config.neo4j.database == "abc123"
        assert config.neo4j.instance_id == "abc123"

    def test_partial_credentials_report_what_is_missing(self) -> None:
        env = {k: v for k, v in FULL_ENV.items() if k != "NEO4J_PASSWORD"}
        config = load_config(env=env, dotenv=False)
        assert config.neo4j is None
        assert any("NEO4J_PASSWORD" in w for w in config.warnings)

    def test_reads_dotenv_file(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# comment\n"
            "NEO4J_URI=neo4j+s://abc123.databases.neo4j.io\n"
            "NEO4J_USERNAME='abc123'\n"
            "NEO4J_PASSWORD=plain-text\n"
            "NEO4J_DATABASE=abc123\n",
            encoding="utf-8",
        )
        config = load_config(env={}, config_dir=tmp_path, dotenv=True)
        assert config.neo4j is not None
        assert config.neo4j is not None
        assert config.neo4j.username == "abc123"
        assert config.neo4j.password.get_secret_value() == "plain-text"

    def test_real_environment_wins_over_the_file(self, tmp_path: Path) -> None:
        env_file = tmp_path / "m0.env"
        env_file.write_text(
            "NEO4J_USERNAME=file-user\nNEO4J_PASSWORD=file-password\n",
            encoding="utf-8",
        )
        config = load_config(
            env={"NEO4J_USERNAME": "environment-user"},
            config_dir=tmp_path,
            dotenv=True,
        )
        assert config.neo4j is None
        assert all("environment-user" not in w for w in config.warnings)
        assert all("file-user" not in w for w in config.warnings)
        assert all("file-password" not in w for w in config.warnings)
        assert any("NEO4J_USERNAME" in w for w in config.warnings)

    def test_environment_takes_priority_over_local_dotenv(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("NEO4J_DATABASE=database-from-file\n", encoding="utf-8")
        env = dict(FULL_ENV)
        env["NEO4J_DATABASE"] = "database-from-environment"
        config = load_config(env=env, config_dir=tmp_path, dotenv=True)
        assert config.neo4j is not None
        assert config.neo4j.database == "database-from-environment"

    def test_gemini_settings_have_defaults(self) -> None:
        config = load_config(env={}, dotenv=False)
        assert config.gemini.embedding_model == "gemini-embedding-2"
        assert config.gemini.embedding_dimensions == 1536
        assert config.has_gemini is False

    def test_gemini_key_is_never_printed(self) -> None:
        config = load_config(env={"GEMINI_API_KEY": "AIza-super-secret"}, dotenv=False)
        assert "AIza-super-secret" not in repr(config)
        assert config.has_gemini is True

    def test_invalid_dimension_falls_back(self) -> None:
        config = load_config(env={"GEMINI_EMBEDDING_DIMENSIONS": "not-a-number"}, dotenv=False)
        assert config.gemini.embedding_dimensions == 1536
        assert any("GEMINI_EMBEDDING_DIMENSIONS" in w for w in config.warnings)

    def test_invalid_uri_is_reported_not_raised(self) -> None:
        env = dict(FULL_ENV)
        env["NEO4J_URI"] = "postgres://localhost/db"
        config = load_config(env=env, dotenv=False)
        assert config.neo4j is None
        assert config.warnings


class TestConfigModel:
    def test_is_frozen(self) -> None:
        config = Config()
        with pytest.raises(ValidationError):
            config.log_level = "DEBUG"  # type: ignore[misc]
