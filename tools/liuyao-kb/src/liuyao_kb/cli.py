"""Command line interface for liuyao-kb.

M1 scope: the skeleton commands only -- ``doctor``, ``sources list`` and
``ingest --dry-run``. Ingestion, embedding and querying arrive in later
milestones.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from liuyao_kb.config import load_config, redact_uri
from liuyao_kb.logging_setup import configure_logging, get_logger

logger = get_logger(__name__)
console = Console()

app = typer.Typer(
    name="liuyao-kb",
    help="Incremental importer and evidence-pack query tool for the Liuyao knowledge base.",
    no_args_is_help=True,
    add_completion=False,
)

sources_app = typer.Typer(help="Inspect the configured source allowlist.")
ingest_app = typer.Typer(help="Import sources into Neo4j.")
app.add_typer(sources_app, name="sources")
app.add_typer(ingest_app, name="ingest")


@app.callback()
def main_callback(
    log_level: Annotated[
        str,
        typer.Option("--log-level", help="DEBUG, INFO, WARNING or ERROR."),
    ] = "INFO",
) -> None:
    """Shared options for every command."""
    configure_logging(log_level)


@app.command()
def doctor(
    json_output: Annotated[bool, typer.Option("--json", help="Print the result as JSON.")] = False,
) -> None:
    """Check the local setup: configuration, credentials and database access.

    Runs without any credentials so it can explain what is missing.
    """
    config = load_config()
    checks: list[dict[str, object]] = []
    report: dict[str, object] = {"checks": checks, "ok": True}

    def record(name: str, ok: bool, detail: str, hint: str | None = None) -> None:
        entry: dict[str, object] = {"name": name, "ok": ok, "detail": detail}
        if hint:
            entry["hint"] = hint
        checks.append(entry)
        if not ok:
            report["ok"] = False

    # --- configuration ----------------------------------------------------
    record(
        "config directory",
        True,
        str(config.config_dir),
    )

    for warning in config.warnings:
        record("configuration warning", False, warning)

    # --- Neo4j ------------------------------------------------------------
    if config.neo4j is None:
        record(
            "Neo4j credentials",
            False,
            "not configured",
            "Set NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD and NEO4J_DATABASE "
            "in your local .env. The values come from the Aura Console instance "
            "credentials file; never commit them.",
        )
    else:
        from liuyao_kb.neo4j.driver import check_connection

        result = check_connection(config.neo4j)
        record(
            "Neo4j connection",
            bool(result["ok"]),
            f"{result['target']} as user {result['username']} on database {result['database']}",
            result.get("hint"),
        )
        if result["ok"]:
            record(
                "Neo4j server",
                True,
                f"Neo4j {result['server_version']} ({result['edition']})",
            )
            record("connection profile", True, str(result["profile"]))

    # --- Gemini -----------------------------------------------------------
    if config.has_gemini:
        record("Gemini API key", True, "configured")
    else:
        checks.append(
            {
                "name": "Gemini API key",
                "ok": True,
                "status": "skipped",
                "detail": "not configured (Gemini is optional until M5)",
                "hint": "Add GEMINI_API_KEY to ~/.config/liuyao-kb/m0.env only when M5 is enabled.",
            }
        )

    # --- output -----------------------------------------------------------
    if json_output:
        console.print_json(json.dumps(report, ensure_ascii=False, default=str))
    else:
        table = Table(title="liuyao-kb doctor", show_lines=True)
        table.add_column("Check", style="bold")
        table.add_column("Status")
        table.add_column("Detail")
        for entry in checks:
            ok = bool(entry["ok"])
            if entry.get("status") == "skipped":
                status = "[yellow]skipped[/yellow]"
            else:
                status = "[green]ok[/green]" if ok else "[yellow]missing[/yellow]"
            table.add_row(str(entry["name"]), status, str(entry["detail"]))
            hint = entry.get("hint")
            if hint:
                table.add_row("", "", f"[dim]{hint}[/dim]")
        console.print(table)
        console.print(
            "[green]All checks passed.[/green]"
            if report["ok"]
            else "[yellow]Some checks need attention.[/yellow]"
        )

    if not report["ok"]:
        raise typer.Exit(code=1)


@sources_app.command("list")
def sources_list(
    sources_path: Annotated[
        Path | None,
        typer.Option("--sources", help="Path to a sources config file."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print the result as JSON.")] = False,
) -> None:
    """List the configured sources and whether each one is enabled."""
    from liuyao_kb.sources.config import find_sources_config, load_sources_config

    resolved = find_sources_config(sources_path)
    if resolved is None:
        console.print(
            "[yellow]No sources config found.[/yellow]\n"
            "Copy sources.example.yaml to sources.yaml and edit it. "
            "Expected locations: ./sources.yaml or "
            "./tools/liuyao-kb/sources.yaml"
        )
        raise typer.Exit(code=1)

    try:
        sources = load_sources_config(resolved)
    except Exception as exc:
        console.print(f"[red]Could not load {resolved}: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    rows = sources.summary()
    if json_output:
        console.print_json(
            json.dumps(
                {"path": str(resolved), "sources": rows},
                ensure_ascii=False,
                default=str,
            )
        )
        return

    table = Table(title=f"Sources ({resolved})", show_lines=True)
    table.add_column("Source", style="bold")
    table.add_column("Enabled")
    table.add_column("Detail")
    table.add_column("Trust", style="dim")
    for row in rows:
        enabled = bool(row["enabled"])
        status = "[green]yes[/green]" if enabled else "[dim]no[/dim]"
        table.add_row(
            str(row["source"]),
            status,
            str(row["detail"]),
            str(row["trust"]),
        )
    console.print(table)
    console.print(
        "[dim]Raw ASR, daily records and external projects stay disabled until "
        "the source is explicitly enabled.[/dim]"
    )


@ingest_app.command("run")
def ingest_run(
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--no-dry-run",
            help="Report what would be imported without calling any API or writing.",
        ),
    ] = True,
    sources_path: Annotated[
        Path | None,
        typer.Option("--sources", help="Path to a sources config file."),
    ] = None,
) -> None:
    """Import the allowlisted sources into Neo4j.

    M1 provides the dry-run scaffold only. Actual parsing, embedding and
    writing arrive in M2 to M5.
    """
    from liuyao_kb.sources.config import find_sources_config, load_sources_config

    config = load_config()
    resolved = find_sources_config(sources_path)
    if resolved is None:
        console.print(
            "[yellow]No sources config found.[/yellow] "
            "Copy sources.example.yaml to sources.yaml first."
        )
        raise typer.Exit(code=1)

    try:
        sources = load_sources_config(resolved)
    except Exception as exc:
        console.print(f"[red]Could not load {resolved}: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold]Dry run[/bold] against {resolved}")
    table = Table(show_lines=True)
    table.add_column("Source", style="bold")
    table.add_column("Enabled")
    table.add_column("Detail")
    for row in sources.summary():
        enabled = bool(row["enabled"])
        status = "[green]yes[/green]" if enabled else "[dim]no[/dim]"
        table.add_row(str(row["source"]), status, str(row["detail"]))
    console.print(table)

    console.print(
        "[yellow]M1 only reports the plan.[/yellow] Parsing, chunking, "
        "embedding and writing land in later milestones (M2-M5)."
    )

    if not dry_run:
        console.print("[red]Refusing to write: ingestion is not implemented until M4.[/red]")
        raise typer.Exit(code=1)

    if config.neo4j is None:
        console.print("[dim]No Neo4j credentials configured; a dry run does not need them.[/dim]")
    else:
        console.print(
            f"[dim]Target: {redact_uri(config.neo4j.uri)} (database {config.neo4j.database})[/dim]"
        )


def main() -> None:
    """Entry point for the ``liuyao-kb`` console script."""
    app()


if __name__ == "__main__":
    main()
