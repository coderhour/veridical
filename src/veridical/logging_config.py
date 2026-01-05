import logging
import sys
from pathlib import Path


def setup_logging(
    level: int | str = logging.INFO, log_file: Path | None = None, verbose: bool = False
) -> None:
    """Configure logging for Veridical.

    Args:
        level: Logging level (int or str)
        log_file: Optional path to a log file
        verbose: If True, set level to DEBUG
    """
    if verbose:
        level = logging.DEBUG
    elif isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    if log_file:
        # Ensure directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )

    # Set some library loggers to WARNING to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("git").setLevel(logging.WARNING)
