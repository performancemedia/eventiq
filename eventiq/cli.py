from __future__ import annotations

from pathlib import Path
from typing import Literal

import typer

from eventiq.logger import setup_logging

from .service import Service
from .utils.imports import import_from_string

cli = typer.Typer()


@cli.command(help="Run service")
def run(
    service_or_runner: str, log_level: str, use_uvloop: bool = typer.Option(False)
) -> None:
    typer.echo(f"Running [{service_or_runner}]...")
    setup_logging(log_level.upper())
    obj = import_from_string(service_or_runner)
    obj.run(use_uvloop=use_uvloop)


@cli.command(help="Watch and reload on files change")
def watch(
    service_or_runner: str = typer.Argument(...),
    log_level: str = typer.Option("INFO"),
    use_uvloop: bool = typer.Option(False),
    directory: str = typer.Option("."),
):
    from watchfiles import run_process

    typer.echo(f"Watching [{service_or_runner}]...")
    setup_logging(log_level.upper())
    obj = import_from_string(service_or_runner)

    def _callback(changes):
        typer.secho(f"Changes detected: {changes}")

    run_process(
        directory,
        target=obj.run,
        kwargs={"use_uvloop": use_uvloop},
        callback=_callback,
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
    format: Literal["json", "yaml"] = typer.Option("json"),
):
    from .asyncapi.generator import get_async_api_spec, save_async_api_to_file

    svc = import_from_string(service)
    if not isinstance(svc, Service):
        typer.secho(f"Service instance expected, got {type(svc)}", fg="red")
    spec = get_async_api_spec(svc)
    save_async_api_to_file(spec, out, format)
    typer.secho(f"Docs saved successfully to {out}", fg="green")
