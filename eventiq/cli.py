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


def _build_target_from_opts(
    service_or_runner: str,
    log_level: Optional[str],
    log_config: Optional[str],
    use_uvloop: Optional[bool],
    debug: Optional[bool],
) -> str:
    cmd = [f"eventiq run {service_or_runner}"]
    if log_level:
        cmd.append(f"--log-level={log_level}")
    if log_config:
        cmd.append(f"--log-config={log_config}")
    if use_uvloop:
        cmd.append("--use-uvloop=true")
    if debug:
        cmd.append("--debug=true")
    return " ".join(cmd)


@cli.command(help="Run service")
def run(
    service_or_runner: str,
    log_level: Optional[str] = typer.Option(
        None,
        help="Logger level, accepted values are: debug, info, warning, error, critical",
    ),
    log_config: Optional[str] = typer.Option(
        None, help="Logging file configuration path."
    ),
    use_uvloop: Optional[bool] = typer.Option(None, help="Enable uvloop"),
    debug: bool = typer.Option(False, help="Enable debug"),
    reload: Optional[str] = typer.Option(None, help="Hot-reload on provided path"),
) -> None:
    if reload:
        try:
            from watchfiles import run_process
        except ImportError:
            logger.error(
                "--reload option requires 'watchfiles' installed. Please run 'pip install watchfiles'."
            )
            return
        logger.info(f"Watching [{service_or_runner}]...")
        target = _build_target_from_opts(
            service_or_runner, log_level, log_config, use_uvloop, debug
        )
        run_process(
            reload,
            target=target,
            target_type="command",
            callback=logger.info,
            sigint_timeout=30,
            sigkill_timeout=30,
        )

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


@cli.command(help="Generate AsyncAPI documentation from service")
def docs(
    service: str = typer.Argument(
        ...,
        help="Global service object to import in format {package}.{module}:{service_object}",
    ),
    version: int = typer.Option(3, help="AsyncAPI version"),
    out: Path = typer.Option("./asyncapi.json", help="Output file path"),
    format: str = typer.Option(
        "json", help="Output format. Valid options are 'yaml' and 'json'(default)"
    ),
):
    from eventiq.asyncapi import resolve_generator

    get_async_api_spec = resolve_generator(version)

    from eventiq.asyncapi.utils import save_async_api_to_file

    svc = import_from_string(service)
    spec = get_async_api_spec(svc)
    save_async_api_to_file(spec, out, format)
    typer.secho(f"Docs saved successfully to {out}", fg="green")
