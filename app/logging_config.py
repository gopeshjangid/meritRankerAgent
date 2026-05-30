"""
app/logging_config.py
---------------------
Centralised logging setup using Rich for readable, colourful output.

Usage (call once at startup):
    from logging_config import configure_logging
    configure_logging("INFO")

Why Rich?
- Time, level, and logger name are colour-coded in the terminal.
- Works well with agentcore dev --logs (plain text fallback when not a TTY).
- Zero performance cost — Rich is already a dependency.
"""

from __future__ import annotations

import logging

from rich.logging import RichHandler

_configured = False


def configure_logging(log_level: str = "INFO") -> None:
    """Attach a RichHandler to the root logger.

    Safe to call multiple times — only configures once per process.

    Args:
        log_level: Standard Python log level string, e.g. "INFO" or "DEBUG".
    """
    global _configured
    if _configured:
        return

    level = logging.getLevelName(log_level.upper())

    logging.basicConfig(
        level=level,
        format="%(message)s",  # Rich formats the rest
        datefmt="[%X]",
        handlers=[
            RichHandler(
                level=level,
                rich_tracebacks=True,
                tracebacks_show_locals=False,  # flip to True for deep debugging
                show_path=True,               # shows module:line
                markup=False,                 # don't interpret [tags] in log msgs
            )
        ],
        force=True,  # replace any handlers already attached (e.g. by Lambda)
    )

    _configured = True
