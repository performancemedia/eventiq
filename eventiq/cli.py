import logging.config
import sys
from pathlib import Path
from typing import Optional

import anyio
import typer

from eventiq.logger import get_logger

from .imports import import_from_string

cli = typer.Typer()

logger = get_logger(__name__, "cli")

if "." not in sys.path:
    sys.path.insert(0, ".")


@cli.command(help="Run service")
def run(
    service_or_runner: str,
    log_level: Optional[str] = typer.Option(None),
    log_config: Optional[str] = typer.Option(None),
    use_uvloop: bool = typer.Option(False),
    debug: bool = typer.Option(False),
) -> None:
    if log_level:
        logging.basicConfig(level=log_level.upper())
    if log_config:
        logging.config.fileConfig(log_config)

    logger.info(f"Running [{service_or_runner}]...")
    obj = import_from_string(service_or_runner)
    if callable(obj):
        obj = obj()
    anyio.run(
        obj.run,
        backend="asyncio",
        backend_options={"use_uvloop": use_uvloop, "debug": debug},
    )


@cli.command(help="Watch and reload on files change")
def watch(
    service_or_runner: str = typer.Argument(...),
    log_level: str = typer.Option("INFO"),
    directory: str = typer.Option("."),
):
    from watchfiles import run_process

    logger.info(f"Watching [{service_or_runner}]...")

    run_process(
        directory,
        target=f"eventiq run {service_or_runner} --log-level={log_level}",
        target_type="command",
        callback=logger.info,
        sigint_timeout=30,
        sigkill_timeout=30,
    )


@cli.command(help="Generate AsyncAPI documentation from service")
def generate_docs(
    service: str = typer.Argument(
        ...,
        help="Global service object to import in format {package}.{module}:{service_object}",
    ),
    out: Path = typer.Option("./asyncapi.json", help="Output file path"),
    format: str = typer.Option(
        "json", help="Output format. Valid options are 'yaml' and 'json'(default)"
    ),
):
    from .asyncapi.generator import get_async_api_spec, save_async_api_to_file

    svc = import_from_string(service)
    spec = get_async_api_spec(svc)
    save_async_api_to_file(spec, out, format)
    typer.secho(f"Docs saved successfully to {out}", fg="green")
