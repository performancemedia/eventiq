from __future__ import annotations

from pathlib import Path

import typer

from eventiq.logger import get_logger, setup_logging

from .service import Service
from .utils.imports import import_from_string

cli = typer.Typer()

logger = get_logger(__name__, "cli")


@cli.command(help="Run service")
def run(
    service_or_runner: str,
    log_level: str = typer.Option(default="info"),
    use_uvloop: bool = typer.Option(False),
) -> None:
    logger.info(f"Running [{service_or_runner}]...")
    setup_logging(log_level.upper())
    obj = import_from_string(service_or_runner)
    obj.run(use_uvloop=use_uvloop)


@cli.command(help="Watch and reload on files change")
def watch(
    service_or_runner: str = typer.Argument(...),
    log_level: str = typer.Option("INFO"),
    directory: str = typer.Option("."),
):
    from watchfiles import run_process

    logger.info(f"Watching [{service_or_runner}]...")
    setup_logging(log_level.upper())

    run_process(
        directory,
        target=f"eventiq run {service_or_runner} --log-level={log_level}",
        target_type="command",
        callback=logger.info,
        sigint_timeout=30,
        sigkill_timeout=30,
    )


@cli.command()
def verify(service: str = typer.Argument(...)) -> None:
    typer.echo(f"Verifying service [{service}]...")
    s = import_from_string(service)
    if not isinstance(s, Service):
        typer.secho(f"Expected Service instance, got {type(s)}", fg="red")
        raise typer.Exit(-1)
    typer.secho("OK", fg="green")


@cli.command()
def generate_docs(
    service: str = typer.Argument(...),
    out: Path = typer.Option("./asyncapi.json"),
    format: str = typer.Option("json"),
):
    from .asyncapi.generator import get_async_api_spec, save_async_api_to_file

    svc = import_from_string(service)
    if not isinstance(svc, Service):
        typer.secho(f"Service instance expected, got {type(svc)}", fg="red")
    spec = get_async_api_spec(svc)
    save_async_api_to_file(spec, out, format)
    typer.secho(f"Docs saved successfully to {out}", fg="green")
