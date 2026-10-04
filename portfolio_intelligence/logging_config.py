"""Logging strutturato condiviso: un logger per modulo, un solo setup globale.

Uso: `log = get_logger(__name__)` in cima al modulo, poi `log.warning(...)`.
Livello configurabile con `LOG_LEVEL` (default INFO); mai usato nei test
(niente I/O di rete nei test, vedi ROADMAP "Principi non negoziabili").
"""

import logging
import os

_CONFIGURED = False


def _configure_once() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Logger per `name` (passare `__name__` del modulo chiamante)."""
    _configure_once()
    return logging.getLogger(name)
