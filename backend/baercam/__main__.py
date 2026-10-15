"""Startpunkt des Backends: `python -m baercam` bzw. die gebaute Sidecar-EXE."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from .server import App, run
from .settings import data_dir


def main() -> None:
    parser = argparse.ArgumentParser(prog="baercam-backend")
    parser.add_argument("--port", type=int, default=0, help="0 = freien Port wählen")
    parser.add_argument("--token", default=None, help="Fester Token (nur für Entwicklung)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(data_dir() / "backend.log", encoding="utf-8"), logging.StreamHandler(sys.stderr)],
    )
    try:
        asyncio.run(run(App(token=args.token), args.port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
